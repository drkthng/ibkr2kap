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
        """Runs the FIFO engine for a specific account, ensuring interleaving of trades and corporate actions."""
        # 1. Clear existing FIFO state for this account context
        self._clear_fifo_data(account_id)
        
        # 2. Fetch all trades for the account
        stmt_trades = (
            select(Trade)
            .where(Trade.account_id == account_id)
            .where(Trade.asset_category != "CASH")
        )
        trades = self.session.execute(stmt_trades).scalars().all()
        
        # 3. Fetch all corporate actions for the account
        from ibkr_tax.models.database import CorporateAction
        stmt_ca = (
            select(CorporateAction)
            .where(CorporateAction.account_id == account_id)
        )
        actions = self.session.execute(stmt_ca).scalars().all()
        
        # 4. Interleave and sort by date. 
        # Trades use 'settle_date', Actions use 'date'.
        # We'll use a consistent key: (date_str, type_priority, id)
        # Type priority: Corporate Actions (0) before Trades (1) on the same date?
        # Usually, a split happens at market open.
        
        events = []
        for t in trades:
            events.append({"date": t.settle_date, "type": "trade", "obj": t, "id": t.id})
        for a in actions:
            events.append({"date": a.date, "type": "action", "obj": a, "id": a.id})
            
        events.sort(key=lambda x: (x["date"], 0 if x["type"] == "action" else 1, x["id"]))
        
        # 5. Process events
        fifo_engine = FIFOEngine(self.session)
        from ibkr_tax.services.corporate_actions import CorporateActionEngine
        ca_engine = CorporateActionEngine(self.session)
        
        for event in events:
            if event["type"] == "trade":
                fifo_engine.process_trade(event["obj"])
            else:
                ca_engine.apply_stock_split(event["obj"])
        
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
