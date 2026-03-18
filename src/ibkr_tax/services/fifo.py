from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import select, asc
from ibkr_tax.models.database import Trade, FIFOLot, Gain

class FIFOEngine:
    def __init__(self, session: Session):
        self.session = session

    def process_trade(self, trade: Trade):
        """Processes a single trade by matching against existing inventory or adding to it."""
        # Try to match against opposite side inventory first
        remaining_to_match = self._match_against_inventory(trade)
        
        if remaining_to_match != 0:
            # If still have quantity, add it as a new lot
            self._add_to_inventory(trade, remaining_to_match)
        else:
            self.session.flush()

    def _add_to_inventory(self, trade: Trade, quantity: Decimal):
        """Creates a new FIFOLot (Long or Short)."""
        # Cost basis in internal currency (already adjusted for options if necessary)
        # For opening trade, we use the full proceeds/commission/taxes
        
        # We need to be careful: if this is a partial opening (after some matching), 
        # the cost_basis should be proportional. 
        # But usually in our flow, we either match fully or create a lot for the remainder.
        
        total_qty = abs(trade.quantity)
        proportion = abs(quantity) / total_qty
        
        cost_in_currency = abs(trade.proceeds) + abs(trade.ib_commission) + abs(trade.taxes)
        cost_basis_eur = (cost_in_currency * trade.fx_rate_to_base) * proportion
        
        lot = FIFOLot(
            trade_id=trade.id,
            asset_category=trade.asset_category,
            symbol=trade.symbol,
            settle_date=trade.settle_date,
            original_quantity=quantity,
            remaining_quantity=quantity,
            cost_basis_total=cost_basis_eur,
            cost_basis_per_share=cost_basis_eur / abs(quantity) if quantity != 0 else Decimal("0"),
            trading_costs_total=(abs(trade.ib_commission) + abs(trade.taxes)) * trade.fx_rate_to_base * proportion
        )

        self.session.add(lot)
        self.session.flush()

    def _match_against_inventory(self, trade: Trade) -> Decimal:
        """
        Matches a trade against existing lots of the opposite side.
        Returns the remaining quantity that could not be matched.
        """
        quantity_to_match = abs(trade.quantity)
        
        # If we are BUYING, we match against existing SHORT lots (quantity < 0)
        # If we are SELLING, we match against existing LONG lots (quantity > 0)
        if trade.buy_sell == "BUY":
            target_sign = -1
            lot_filter = FIFOLot.remaining_quantity < 0
        else:
            target_sign = 1
            lot_filter = FIFOLot.remaining_quantity > 0
            
        stmt = (
            select(FIFOLot)
            .where(FIFOLot.symbol == trade.symbol)
            .where(FIFOLot.asset_category == trade.asset_category)
            .where(lot_filter)
            .order_by(asc(FIFOLot.settle_date), asc(FIFOLot.id))
        )
        open_lots = self.session.execute(stmt).scalars().all()
        # print(f"DEBUG: Found {len(open_lots)} lots for {trade.symbol} side {trade.buy_sell}")
        
        if not open_lots:
            return trade.quantity
            
        # Proceeds/Cost for the matching trade
        # For SELL (closing long), it's Proceeds.
        # For BUY (closing short), it's negative Proceeds (Cost to buy back).
        # We'll use the logic: realized_pnl = cash_out_total - cash_in_total?
        # Standard: realized_pnl = proceeds - cost_basis
        
        # Net amount in EUR for this entire trade
        net_currency = trade.proceeds - abs(trade.ib_commission) - abs(trade.taxes)
        net_eur_total = net_currency * trade.fx_rate_to_base
        
        eur_per_unit = net_eur_total / quantity_to_match if quantity_to_match != 0 else Decimal("0")
        
        current_qty_to_match = quantity_to_match
        for lot in open_lots:
            if current_qty_to_match <= 0:
                break
                
            matched_qty = min(abs(lot.remaining_quantity), current_qty_to_match)
            
            # Cost basis defined by the opening lot
            # lot.cost_basis_total is ALWAYS positive in our DB (as per _add_to_inventory)
            cost_basis_matched = (matched_qty / abs(lot.original_quantity)) * lot.cost_basis_total
            
            # Proceeds from the closing trade
            proceeds_matched = matched_qty * eur_per_unit
            
            # realized_pnl calculation
            # If closing LONG (SELL): pnl = proceeds - cost
            # If closing SHORT (BUY): pnl = cost_received - cost_to_buy_back
            # Wait, lot.cost_basis_total for SHORT is premium received (positive).
            # proceeds_matched for BUY is negative (cost to buy back).
            # So pnl = lot_cost + trade_proceeds?
            # Example: Short for 100. Buy back for 80. pnl = 100 + (-80) = 20. Correct.
            # Example: Short for 100. Buy back for 120. pnl = 100 + (-120) = -20. Correct.
            # Example: Long for 80. Sell for 100. pnl = 100 - 80 = 20. Correct.
            
            if target_sign == 1: # Closing LONG
                pnl = proceeds_matched - cost_basis_matched
                real_proceeds = proceeds_matched
                real_cost = cost_basis_matched
            else: # Closing SHORT
                pnl = cost_basis_matched + proceeds_matched
                real_proceeds = cost_basis_matched
                real_cost = -proceeds_matched
            
            # Proportional trading costs
            buy_side_comm = (matched_qty / abs(lot.original_quantity)) * lot.trading_costs_total
            sell_side_comm = (matched_qty / quantity_to_match) * (abs(trade.ib_commission) + abs(trade.taxes)) * trade.fx_rate_to_base

            gain = Gain(
                sell_trade_id=trade.id,
                buy_lot_id=lot.id,
                quantity_matched=matched_qty,
                tax_year=int(trade.settle_date[:4]),
                proceeds=real_proceeds,
                cost_basis_matched=real_cost,
                realized_pnl=pnl,
                buy_comm=buy_side_comm,
                sell_comm=sell_side_comm,
                tax_pool=self._determine_tax_pool(trade)
            )


            self.session.add(gain)
            
            # Update lot
            lot.remaining_quantity += (matched_qty if target_sign == -1 else -matched_qty)
            current_qty_to_match -= matched_qty
            
        remaining_qty = current_qty_to_match * (1 if trade.buy_sell == "BUY" else -1)
        return remaining_qty

    def _determine_tax_pool(self, trade: Trade) -> str:
        """Determines the tax pool based on asset category."""
        if trade.asset_category == "STK":
            return "Aktien"
        elif trade.asset_category == "OPT":
            return "Termingeschäfte"
        else:
            return "Sonstige"
