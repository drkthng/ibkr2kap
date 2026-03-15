from decimal import Decimal
from typing import List
from sqlalchemy import select, asc
from sqlalchemy.orm import Session

from ibkr_tax.models.database import FIFOLot, Gain, Trade as DBTrade
from ibkr_tax.schemas.ibkr import OptionEAECreate, TradeSchema


class OptionEngine:
    """
    Engine to handle Option Exercise, Assignment, and Expiration (EAE).
    Adjusts underlying stock trades and closes option lots.
    """

    def __init__(self, session: Session):
        self.session = session

    def apply_option_adjustments(
        self, eae_records: List[OptionEAECreate]
    ):
        """
        Processes OptionEAE records.
        Closes existing option FIFOLots and adjusts underlying stock Trades in the database.
        """
        for eae in eae_records:
            if eae.transaction_type == "Expiration":
                self._handle_expiration(eae)
            elif eae.transaction_type in ["Exercise", "Assignment"]:
                self._handle_exercise_assignment(eae)

    def _handle_expiration(self, eae: OptionEAECreate):
        """Creates a synthetic trade to close an option lot at zero value."""
        # Find the open lot for this option to know the account and quantity to close
        lot = self._find_option_lot(eae)
        if not lot:
            return

        # Create a synthetic closing trade
        # ib_trade_id must be unique.
        synthetic_id = f"SYNT_EAE_{eae.symbol}_{eae.date.isoformat()}_{eae.transaction_type}"
        
        # Check if already exists to ensure idempotency
        existing = self.session.execute(
            select(DBTrade).where(DBTrade.ib_trade_id == synthetic_id)
        ).scalar()
        if existing:
            return
            
        # Closing quantity is the opposite of remaining quantity
        close_qty = -lot.remaining_quantity
        buy_sell = "BUY" if close_qty > 0 else "SELL"
        
        from ibkr_tax.models.database import Account
        account_id = self.session.execute(
            select(Account.id).where(Account.account_id == eae.account_id)
        ).scalar()

        synthetic_trade = DBTrade(
            ib_trade_id=synthetic_id,
            account_id=account_id,
            asset_category="OPT",
            symbol=eae.symbol,
            description=f"Option {eae.transaction_type} (Synthetic)",
            trade_date=eae.date.isoformat(),
            settle_date=eae.date.isoformat(),
            currency=eae.currency,
            fx_rate_to_base=eae.fx_rate_to_base,
            quantity=close_qty,
            trade_price=Decimal("0"),
            proceeds=Decimal("0"),
            buy_sell=buy_sell,
            open_close_indicator="C"
        )
        self.session.add(synthetic_trade)
        self.session.flush()

    def _handle_exercise_assignment(self, eae: OptionEAECreate):
        """Adjusts stock trade and closes option lot."""
        lot = self._find_option_lot(eae)
        if not lot:
            return

        # Find the corresponding stock trade in the database
        target_qty = abs(eae.quantity * eae.multiplier)
        
        # We need to find the internal account.id
        from ibkr_tax.models.database import Account
        account_id = self.session.execute(
            select(Account.id).where(Account.account_id == eae.account_id)
        ).scalar()
        
        stmt = (
            select(DBTrade)
            .where(DBTrade.account_id == account_id)
            .where(DBTrade.symbol == eae.underlying_symbol)
            .where(DBTrade.trade_date == eae.date.isoformat())
        )
        candidates = self.session.execute(stmt).scalars().all()
        
        target_trade = None
        for t in candidates:
             if abs(t.quantity) == target_qty and abs(t.trade_price - eae.strike) < Decimal("0.01"):
                target_trade = t
                break
        
        if not target_trade:
            return

        # Option premium in currency
        premium_in_currency = lot.cost_basis_total / eae.fx_rate_to_base
        
        if lot.remaining_quantity < 0:
            target_trade.proceeds += premium_in_currency
        else:
            target_trade.proceeds -= premium_in_currency

        # Mark option lot as closed
        lot.remaining_quantity = Decimal("0")
        self.session.flush()

    def _find_option_lot(self, eae: OptionEAECreate) -> FIFOLot:
        stmt = (
            select(FIFOLot)
            .where(FIFOLot.symbol == eae.symbol)
            .where(FIFOLot.asset_category == "OPT")
            .where(FIFOLot.remaining_quantity != 0)
            .order_by(asc(FIFOLot.settle_date))
        )
        return self.session.execute(stmt).scalars().first()
