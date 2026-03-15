from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import select, asc
from ibkr_tax.models.database import Trade, FIFOLot, Gain

class FIFOEngine:
    def __init__(self, session: Session):
        self.session = session

    def process_trade(self, trade: Trade):
        """Processes a single trade, either adding to inventory (BUY) or realizing gains (SELL)."""
        if trade.buy_sell == "BUY":
            self._add_to_inventory(trade)
        elif trade.buy_sell == "SELL":
            self._realize_gains(trade)

    def _add_to_inventory(self, trade: Trade):
        """Creates a new FIFOLot from a BUY trade."""
        # Cost basis in EUR = (abs(proceeds) + abs(commission) + abs(taxes)) * 1.0 (if proceeds already in EUR)
        # Wait, Trade.proceeds/commission/taxes are in Trade.currency.
        # We need them in EUR using Trade.fx_rate_to_base.
        
        # IBKR proceeds is already the negative cash flow for BUY.
        # Total cost in trade currency = abs(trade.proceeds) + abs(trade.ib_commission) + abs(trade.taxes)
        cost_in_currency = abs(trade.proceeds) + abs(trade.ib_commission) + abs(trade.taxes)
        cost_basis_eur = cost_in_currency * trade.fx_rate_to_base
        
        lot = FIFOLot(
            trade_id=trade.id,
            asset_category=trade.asset_category,
            symbol=trade.symbol,
            settle_date=trade.settle_date,
            original_quantity=trade.quantity,
            remaining_quantity=trade.quantity,
            cost_basis_total=cost_basis_eur,
            cost_basis_per_share=cost_basis_eur / trade.quantity if trade.quantity != 0 else Decimal("0")
        )
        self.session.add(lot)
        self.session.flush()

    def _realize_gains(self, trade: Trade):
        """Matches a SELL trade against open FIFOLots."""
        # SELL quantity is negative, we need the absolute amount to match.
        quantity_to_match = abs(trade.quantity)
        
        # Fetch open lots for this symbol, ordered by settle_date ASC (FIFO)
        stmt = (
            select(FIFOLot)
            .where(FIFOLot.symbol == trade.symbol)
            .where(FIFOLot.asset_category == trade.asset_category)
            .where(FIFOLot.remaining_quantity > 0)
            .order_by(asc(FIFOLot.settle_date), asc(FIFOLot.id))
        )
        open_lots = self.session.execute(stmt).scalars().all()
        
        # Calculate total proceeds in EUR for this trade
        # Proceeds are cash in (positive). Net proceeds = proceeds - abs(commission) - abs(taxes)
        net_proceeds_currency = trade.proceeds - abs(trade.ib_commission) - abs(trade.taxes)
        proceeds_eur_total = net_proceeds_currency * trade.fx_rate_to_base
        
        # We'll calculate proceeds per unit to distribute among matched lots
        proceeds_per_unit_eur = proceeds_eur_total / quantity_to_match if quantity_to_match != 0 else Decimal("0")
        
        for lot in open_lots:
            if quantity_to_match <= 0:
                break
            
            matched_qty = min(lot.remaining_quantity, quantity_to_match)
            
            # Calculate cost basis for this matched portion
            # We use the proportional cost basis based on original quantity to avoid rounding drift if possible,
            # or just use cost_basis_per_share.
            # German tax law usually requires 4-6 decimals for per-share, but keeping total-based is safer.
            cost_basis_matched_eur = (matched_qty / lot.original_quantity) * lot.cost_basis_total
            
            # Proceeds for this matched portion
            proceeds_matched_eur = matched_qty * proceeds_per_unit_eur
            
            # Create Gain record
            gain = Gain(
                sell_trade_id=trade.id,
                buy_lot_id=lot.id,
                quantity_matched=matched_qty,
                tax_year=int(trade.settle_date[:4]), # Extract year from ISO date YYYY-MM-DD
                proceeds=proceeds_matched_eur,
                cost_basis_matched=cost_basis_matched_eur,
                realized_pnl=proceeds_matched_eur - cost_basis_matched_eur,
                tax_pool=self._determine_tax_pool(trade)
            )
            self.session.add(gain)
            
            # Update lot
            lot.remaining_quantity -= matched_qty
            quantity_to_match -= matched_qty
            
        if quantity_to_match > 0:
            # This is a "Short" opening. Create a FIFOLot with negative quantity.
            self._add_to_inventory(trade)
        
        self.session.flush()

    def _determine_tax_pool(self, trade: Trade) -> str:
        """Determines the tax pool based on asset category."""
        if trade.asset_category == "STK":
            return "Aktien"
        elif trade.asset_category == "OPT":
            return "Termingeschäfte"
        else:
            return "Sonstige"
