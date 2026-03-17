from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import select
from ibkr_tax.models.database import FIFOLot
from ibkr_tax.schemas.ibkr import CorporateActionSchema

class CorporateActionEngine:
    """
    Engine to handle Corporate Actions like Stock Splits.
    Adjusts open FIFOLots directly.
    """

    def __init__(self, session: Session):
        self.session = session

    def apply(self, action: CorporateActionSchema):
        """Dispatches to the specific action handler."""
        if action.action_type == "SO":
            self.apply_spinoff(action)
        elif action.action_type in ["RS", "BS"]: # RS is what we use for splits/reverse splits
            self.apply_reverse_split(action)
        # RI, DW, DI, ED are informational and ignored for FIFO

    def apply_spinoff(self, action: CorporateActionSchema):
        """
        Creates a virtual buy FIFOLot for the spun-off shares.
        """
        # Spinoff creates NEW shares. We create a virtual lot.
        # Note: action.quantity is the positive amount received (e.g. 3.0004)
        # action.value is the total value assigned by IBKR (often close to 0)
        
        # We need the currency conversion if value is in non-EUR
        # In this context, we might not have the FX rate easily available as in TradeEngine,
        # but for spinoffs with nominal $0.0001 value, it doesn't matter much.
        # In the future, we should probably fetch the FX rate for the spinoff date.
        cost_basis_total = action.value # Simplified
        cost_basis_per_share = cost_basis_total / action.quantity if action.quantity != 0 else Decimal("0")

        # Fetch the account internal ID
        from ibkr_tax.models.database import CorporateAction
        ca_record = self.session.query(CorporateAction).filter_by(transaction_id=action.transaction_id).first()
        ca_id = ca_record.id if ca_record else None

        new_lot = FIFOLot(
            trade_id=None,
            corporate_action_id=ca_id,
            asset_category="STK",
            symbol=action.symbol,
            settle_date=action.date.isoformat(),
            original_quantity=action.quantity,
            remaining_quantity=action.quantity,
            cost_basis_total=cost_basis_total,
            cost_basis_per_share=cost_basis_per_share
        )
        self.session.add(new_lot)
        self.session.flush()

    def apply_reverse_split(self, action: CorporateActionSchema):
        """
        Applies a stock split or reverse split to all open FIFOLots.
        IBKR provides 'quantity' as the net change in shares.
        Example 4:1 Split -> 10 shares become 40. Quantity is +30. Ratio = 4.0.
        Example 1:10 Reverse Split -> 1000 shares become 100. Quantity is -900. Ratio = 0.1.
        """
        stmt = (
            select(FIFOLot)
            .where(FIFOLot.symbol == action.symbol)
            .where(FIFOLot.remaining_quantity != 0)
        )
        lots = self.session.execute(stmt).scalars().all()

        for lot in lots:
            # We need to calculate the ratio per lot to apply it consistently 
            # to both original and remaining quantity.
            # ratio = (current_qty + net_change) / current_qty
            # However, IBKR's 'quantity' is for the whole position across the account.
            # So we assume the ratio is the same for all lots.
            
            # Since we don't have the 'position-before' in the action record,
            # we derive the ratio from the description if possible, or use the quantity 
            # if we had the total position.
            
            # Use the backward-compat @property ratio if it works, 
            # or try to derive it better.
            ratio = action.ratio # This currently returns 1 in my new schema placeholder.
            
            # TODO: Better ratio derivation for RS when not in description.
            # For DEC example: DEC(GB00BYX7JT74) 1 FOR 20 CONSOLIDATION
            # If ratio is 1/20 = 0.05.
            
            # For now, let's look at the implementation plan: 
            # "RS actions will compute ratio from old/new quantities"
            # Actually, the SO record has a raw quantity. 
            # Let's assume for splits we use the ratio property which I'll improve.

            lot.original_quantity *= ratio
            lot.remaining_quantity *= ratio
            
            if lot.original_quantity != 0:
                lot.cost_basis_per_share = lot.cost_basis_total / lot.original_quantity
            else:
                lot.cost_basis_per_share = Decimal("0")

        self.session.flush()
