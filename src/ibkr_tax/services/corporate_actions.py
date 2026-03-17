from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import select
from ibkr_tax.models.database import FIFOLot
from ibkr_tax.schemas.ibkr import CorporateActionSchema

class CorporateActionEngine:
    """
    Engine to handle Corporate Actions like Stock Splits, Reverse Splits, and Spinoffs.
    Adjusts open FIFOLots directly.
    """

    def __init__(self, session: Session):
        self.session = session

    def apply(self, action: CorporateActionSchema):
        """Dispatches to the specific action handler."""
        if action.action_type == "SO":
            self.apply_spinoff(action)
        elif action.action_type in ("RS", "FS"):
            self.apply_split(action)
        # RI, DW, DI, ED are informational and ignored for FIFO

    def apply_spinoff(self, action: CorporateActionSchema):
        """
        Creates a virtual buy FIFOLot for the spun-off shares.
        """
        cost_basis_total = action.value
        cost_basis_per_share = cost_basis_total / action.quantity if action.quantity != 0 else Decimal("0")

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

    def apply_split(self, action: CorporateActionSchema):
        """
        Applies a stock split or reverse split to all open FIFOLots.

        Handles two cases:
        1. Simple split (no symbol rename): ratio applied to lots matching action.symbol
        2. Split with symbol rename (reverse split consolidation):
           - action.parent_symbol = old symbol (lots to find)
           - action.symbol = new symbol (rename lots to this)
           - ratio computed from grouped records in group_split_actions()

        Cost basis total is preserved (tax-neutral under German law).
        cost_basis_per_share is recalculated after quantity adjustment.
        """
        # Determine old and new symbols
        old_symbol = action.parent_symbol if action.parent_symbol else action.symbol
        new_symbol = action.symbol

        # Determine if this is a symbol rename (old != new and old doesn't end with .OLD)
        is_rename = old_symbol != new_symbol

        # Look up lots by the old symbol (or current symbol for simple splits)
        lookup_symbol = old_symbol
        if is_rename and not old_symbol.endswith(".OLD"):
            # For grouped events where parent_symbol is set to DEC.OLD,
            # we need to find lots under the ORIGINAL symbol before IBKR renamed it.
            # The original symbol is the new symbol (DEC) since IBKR trades used DEC.
            # But after grouping, parent_symbol = DEC.OLD (the removal leg).
            # Actually, we need to look for lots matching the original trade symbol.
            # Since trades were bought under "DEC" and the .OLD records reference "DEC.OLD",
            # we look for lots under the base symbol (strip .OLD suffix from parent if present).
            lookup_symbol = old_symbol
        
        # If old symbol ends with .OLD, the real lots are under the base name
        if old_symbol.endswith(".OLD"):
            lookup_symbol = old_symbol.replace(".OLD", "")

        stmt = (
            select(FIFOLot)
            .where(FIFOLot.symbol == lookup_symbol)
            .where(FIFOLot.remaining_quantity != 0)
        )
        lots = self.session.execute(stmt).scalars().all()

        ratio = action.ratio

        for lot in lots:
            # Adjust quantities by ratio
            lot.original_quantity *= ratio
            lot.remaining_quantity *= ratio

            # Rename symbol if needed
            if is_rename or old_symbol.endswith(".OLD"):
                lot.symbol = new_symbol

            # Recalculate cost_basis_per_share (total cost unchanged, tax-neutral)
            if lot.original_quantity != 0:
                lot.cost_basis_per_share = lot.cost_basis_total / lot.original_quantity
            else:
                lot.cost_basis_per_share = Decimal("0")

        self.session.flush()
