from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import select

from ibkr_tax.models.database import Transfer, FIFOLot


class TransferEngine:
    """Processes inter-account transfers to create FIFOLots for incoming stock positions.
    
    German Tax Law: Inter-account transfers between a taxpayer's own accounts
    are not taxable events. The cost basis (Anschaffungskosten) carries over 1:1.
    """

    def __init__(self, session: Session):
        self.session = session

    def process_transfers(self, account_id: int) -> int:
        """Creates FIFOLots for IN-direction stock transfers for a given account.
        
        Args:
            account_id: Internal DB account ID
            
        Returns:
            Number of FIFOLots created
        """
        stmt = (
            select(Transfer)
            .where(Transfer.account_id == account_id)
            .where(Transfer.direction == "IN")
            .where(Transfer.quantity > 0)
            .where(Transfer.symbol != "--")
            .order_by(Transfer.settle_date)
        )
        transfers = self.session.execute(stmt).scalars().all()

        lots_created = 0
        for transfer in transfers:
            # Idempotency: skip if lot already exists for this transfer
            existing = self.session.execute(
                select(FIFOLot).where(FIFOLot.transfer_id == transfer.id)
            ).scalar()
            if existing:
                continue

            quantity = transfer.quantity
            # Use positionAmountInBase as cost basis (already in EUR)
            cost_basis_total = abs(transfer.position_amount_in_base)

            if quantity == 0:
                continue

            cost_basis_per_share = cost_basis_total / abs(quantity)

            lot = FIFOLot(
                trade_id=None,
                corporate_action_id=None,
                transfer_id=transfer.id,
                asset_category="STK",
                symbol=transfer.symbol,
                settle_date=transfer.settle_date,
                original_quantity=quantity,
                remaining_quantity=quantity,
                cost_basis_total=cost_basis_total,
                cost_basis_per_share=cost_basis_per_share,
                trading_costs_total=Decimal("0")
            )

            self.session.add(lot)
            lots_created += 1

        self.session.flush()
        return lots_created

    def _process_single_transfer(self, transfer: Transfer) -> None:
        """Process a single transfer record to create a FIFOLot.
        
        Used by FIFORunner for interleaved event processing.
        """
        # Idempotency: skip if lot already exists
        existing = self.session.execute(
            select(FIFOLot).where(FIFOLot.transfer_id == transfer.id)
        ).scalar()
        if existing:
            return

        quantity = transfer.quantity
        cost_basis_total = abs(transfer.position_amount_in_base)

        if quantity == 0:
            return

        cost_basis_per_share = cost_basis_total / abs(quantity)

        lot = FIFOLot(
            trade_id=None,
            corporate_action_id=None,
            transfer_id=transfer.id,
            asset_category="STK",
            symbol=transfer.symbol,
            settle_date=transfer.settle_date,
            original_quantity=quantity,
            remaining_quantity=quantity,
            cost_basis_total=cost_basis_total,
            cost_basis_per_share=cost_basis_per_share,
            trading_costs_total=Decimal("0")
        )

        self.session.add(lot)
        self.session.flush()
