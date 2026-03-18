from sqlalchemy.orm import Session
from sqlalchemy import select, asc, delete
from ibkr_tax.models.database import Account, Trade, FIFOLot, Gain, CorporateAction, Transfer, ManualPosition
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
        
        # 4. Fetch all stock transfers (IN direction) for the account
        stmt_transfers = (
            select(Transfer)
            .where(Transfer.account_id == account_id)
            .where(Transfer.direction == "IN")
            .where(Transfer.quantity > 0)
            .where(Transfer.symbol != "--")
        )
        transfers = self.session.execute(stmt_transfers).scalars().all()
        
        # 5. Fetch all manual positions for the account
        stmt_manual = (
            select(ManualPosition)
            .where(ManualPosition.account_id == account_id)
        )
        manual_positions = self.session.execute(stmt_manual).scalars().all()
        
        # 6. Convert DB models to schemas and group split actions
        action_schemas = [CorporateActionSchema.model_validate(a) for a in db_actions]
        
        from ibkr_tax.services.flex_parser import FlexXMLParser
        grouped_actions = FlexXMLParser._group_split_actions_static(action_schemas)
        
        # 7. Interleave and sort by date. 
        # Type priority: Manual (-1) before Transfers (0) before Corporate Actions (1) before Trades (2).
        
        events = []
        for t in trades:
            events.append({"date": t.settle_date, "type": "trade", "obj": t, "id": t.id})
        for idx, a in enumerate(grouped_actions):
            events.append({"date": a.date.isoformat(), "type": "action", "obj": a, "id": idx})
        for xfer in transfers:
            events.append({"date": xfer.settle_date, "type": "transfer", "obj": xfer, "id": xfer.id})
        for mp in manual_positions:
            events.append({"date": mp.acquisition_date, "type": "manual", "obj": mp, "id": mp.id})
        
        type_priority = {"manual": -1, "transfer": 0, "action": 1, "trade": 2}
        events.sort(key=lambda x: (x["date"], type_priority.get(x["type"], 99), x["id"]))
        
        # 7. Process events
        fifo_engine = FIFOEngine(self.session)
        from ibkr_tax.services.corporate_actions import CorporateActionEngine
        ca_engine = CorporateActionEngine(self.session)
        from ibkr_tax.services.transfer_engine import TransferEngine
        transfer_engine = TransferEngine(self.session)
        
        for event in events:
            if event["type"] == "trade":
                fifo_engine.process_trade(event["obj"])
            elif event["type"] == "action":
                ca_engine.apply(event["obj"])
            elif event["type"] == "transfer":
                # Process individual transfer — create FIFOLot
                transfer_engine._process_single_transfer(event["obj"])
            elif event["type"] == "manual":
                self._process_manual_position(event["obj"], fifo_engine)

        
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

        # Also delete FIFOLots from transfers for this account
        transfer_ids_stmt = select(Transfer.id).where(Transfer.account_id == account_id)
        transfer_ids = self.session.execute(transfer_ids_stmt).scalars().all()
        if transfer_ids:
            self.session.execute(
                delete(FIFOLot).where(FIFOLot.transfer_id.in_(transfer_ids))
            )

        # Also delete FIFOLots from manual positions for this account
        mp_ids_stmt = select(ManualPosition.id).where(ManualPosition.account_id == account_id)
        mp_ids = self.session.execute(mp_ids_stmt).scalars().all()
        if mp_ids:
            self.session.execute(
                delete(FIFOLot).where(FIFOLot.manual_position_id.in_(mp_ids))
            )
        
        self.session.flush()

    def _process_manual_position(self, mp, fifo_engine):
        """Processes a ManualPosition, either as a direct FIFOLot or as a synthetic Trade."""
        if mp.buy_sell:
            # Synthetic Trade for FIFO matching (allows matching closing trades provided manually)
            from ibkr_tax.models.database import Trade
            
            # Manual entries use positive quantity in UI, but Trade expects signed.
            # In add_manual_position, we save mp.quantity as is.
            # If BUY, quantity > 0. If SELL, quantity < 0.
            signed_qty = mp.quantity if mp.buy_sell == "BUY" else -mp.quantity
            
            mock_trade = Trade(
                id=-(1000000 + mp.id), # Negative ID to avoid collision with real trades
                ib_trade_id=f"MANUAL_{mp.id}",
                symbol=mp.symbol,
                asset_category=mp.asset_category,
                quantity=signed_qty,
                buy_sell=mp.buy_sell,
                open_close_indicator=mp.open_close_indicator or "O",
                proceeds=mp.proceeds or 0,
                ib_commission=mp.ib_commission or 0,
                taxes=mp.taxes or 0,
                fx_rate_to_base=mp.fx_rate_to_base or 1.0,
                settle_date=mp.acquisition_date,
                trade_date=mp.trade_date or mp.acquisition_date,
                description=mp.description,
                currency=mp.currency
            )
            fifo_engine.process_trade(mock_trade)
            
            # If there's a leftover lot, we need to link it to the manual position ID 
            # instead of a trade ID if possible, but FIFOEngine._add_to_inventory 
            # currently always sets trade_id=trade.id.
            # However, for manual closure tracking, this synthetic trade approach is sufficient
            # to generate Gains.
            return

        # Legacy / Simple Opening Lot logic
        quantity = mp.quantity
        cost_basis = mp.cost_basis_total_eur
        if quantity == 0:
            return
        lot = FIFOLot(
            trade_id=None,
            corporate_action_id=None,
            transfer_id=None,
            manual_position_id=mp.id,
            asset_category=mp.asset_category,
            symbol=mp.symbol,
            settle_date=mp.acquisition_date,
            original_quantity=quantity,
            remaining_quantity=quantity,
            cost_basis_total=cost_basis or (mp.proceeds * mp.fx_rate_to_base) if mp.proceeds else 0,
            cost_basis_per_share=(cost_basis or (mp.proceeds * mp.fx_rate_to_base)) / abs(quantity) if quantity != 0 else 0,
        )
        self.session.add(lot)
        self.session.flush()

