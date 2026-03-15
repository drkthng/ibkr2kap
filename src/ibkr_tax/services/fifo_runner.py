from sqlalchemy.orm import Session
from sqlalchemy import select, asc, delete
from ibkr_tax.models.database import Account, Trade, FIFOLot, Gain
from ibkr_tax.services.fifo import FIFOEngine

class FIFORunner:
    def __init__(self, session: Session):
        self.session = session

    def run_all(self):
        """Runs the FIFO engine for all accounts in the database."""
        accounts = self.session.execute(select(Account)).scalars().all()
        for account in accounts:
            self.run_for_account(account.id)

    def run_for_account(self, account_id: int):
        """Runs the FIFO engine for a specific account, ensuring idempotency by clearing existing FIFO data."""
        # 1. Clear existing FIFO state for this account context
        self._clear_fifo_data(account_id)
        
        # 2. Fetch all trades for the account, ordered by settle_date then id
        stmt = (
            select(Trade)
            .where(Trade.account_id == account_id)
            .order_by(asc(Trade.settle_date), asc(Trade.id))
        )
        trades = self.session.execute(stmt).scalars().all()
        
        # 3. Process each trade through the engine
        engine = FIFOEngine(self.session)
        for trade in trades:
            engine.process_trade(trade)
        
        self.session.commit()

    def _clear_fifo_data(self, account_id: int):
        """Deletes all Gain and FIFOLot records associated with the account's trades."""
        # Due to foreign keys, we delete Gains first
        # Gains are linked to Sell trades. Sell trades are linked to Account.
        
        # Subquery to find trade IDs for this account
        trade_ids_stmt = select(Trade.id).where(Trade.account_id == account_id)
        trade_ids = self.session.execute(trade_ids_stmt).scalars().all()
        
        if not trade_ids:
            return

        # Delete Gains where sell_trade_id belongs to this account
        self.session.execute(
            delete(Gain).where(Gain.sell_trade_id.in_(trade_ids))
        )
        
        # Delete FIFOLots where trade_id belongs to this account
        self.session.execute(
            delete(FIFOLot).where(FIFOLot.trade_id.in_(trade_ids))
        )
        
        self.session.flush()
