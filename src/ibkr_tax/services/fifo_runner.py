from sqlalchemy.orm import Session
from sqlalchemy import select, asc, delete
from ibkr_tax.models.database import Account, Trade, FIFOLot, Gain, CorporateAction
from ibkr_tax.services.fifo import FIFOEngine
from ibkr_tax.schemas.ibkr import CorporateActionSchema

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
        db_actions = self.session.execute(stmt_ca).scalars().all()
        
        # 4. Convert DB models to schemas and group split actions
        action_schemas = [CorporateActionSchema.model_validate(a) for a in db_actions]
        
        from ibkr_tax.services.flex_parser import FlexXMLParser
        # Use the grouping function (it's a method but we can call it with a dummy instance
        # or make it work standalone — for now we instantiate minimally)
        grouped_actions = FlexXMLParser._group_split_actions_static(action_schemas)
        
        # 5. Interleave and sort by date. 
        # Trades use 'settle_date', Actions use 'date'.
        # Type priority: Corporate Actions (0) before Trades (1) on the same date.
        
        events = []
        for t in trades:
            events.append({"date": t.settle_date, "type": "trade", "obj": t, "id": t.id})
        for idx, a in enumerate(grouped_actions):
            events.append({"date": a.date.isoformat(), "type": "action", "obj": a, "id": idx})
            
        events.sort(key=lambda x: (x["date"], 0 if x["type"] == "action" else 1, x["id"]))
        
        # 6. Process events
        fifo_engine = FIFOEngine(self.session)
        from ibkr_tax.services.corporate_actions import CorporateActionEngine
        ca_engine = CorporateActionEngine(self.session)
        
        for event in events:
            if event["type"] == "trade":
                fifo_engine.process_trade(event["obj"])
            else:
                ca_engine.apply(event["obj"])
        
        self.session.commit()

    def _clear_fifo_data(self, account_id: int):
        """Deletes all Gain and FIFOLot records associated with the account."""
        # Delete Gains first
        trade_ids_stmt = select(Trade.id).where(Trade.account_id == account_id)
        trade_ids = self.session.execute(trade_ids_stmt).scalars().all()
        
        if trade_ids:
            self.session.execute(
                delete(Gain).where(Gain.sell_trade_id.in_(trade_ids))
            )
            self.session.execute(
                delete(FIFOLot).where(FIFOLot.trade_id.in_(trade_ids))
            )

        # Also delete FIFOLots from corporate actions for this account
        ca_ids_stmt = select(CorporateAction.id).where(CorporateAction.account_id == account_id)
        ca_ids = self.session.execute(ca_ids_stmt).scalars().all()
        if ca_ids:
            self.session.execute(
                delete(FIFOLot).where(FIFOLot.corporate_action_id.in_(ca_ids))
            )
        
        self.session.flush()
