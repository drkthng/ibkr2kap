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

    def apply_stock_split(self, action: CorporateActionSchema):
        """
        Applies a stock split to all open FIFOLots for the given symbol.
        Formula:
          new_quantity = old_quantity * ratio
          new_cost_basis_per_share = old_cost_basis_per_share / ratio
          cost_basis_total = stays the same
        """
        stmt = (
            select(FIFOLot)
            .where(FIFOLot.symbol == action.symbol)
            .where(FIFOLot.remaining_quantity != 0)
        )
        lots = self.session.execute(stmt).scalars().all()

        for lot in lots:
            # Update quantities
            lot.original_quantity *= action.ratio
            lot.remaining_quantity *= action.ratio
            
            # Update cost basis per share to avoid precision drift, 
            # though cost_basis_total remains the source of truth in FIFOEngine.
            # cost_basis_per_share = cost_basis_total / original_quantity (new)
            if lot.original_quantity != 0:
                lot.cost_basis_per_share = lot.cost_basis_total / lot.original_quantity
            else:
                lot.cost_basis_per_share = Decimal("0")

        self.session.flush()
