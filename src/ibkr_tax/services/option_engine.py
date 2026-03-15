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
        self, eae_records: List[OptionEAECreate], trades: List[TradeSchema]
    ):
        """
        Processes OptionEAE records and adjusts the provided transient TradeSchema list.
        Closes existing option FIFOLots in the database.
        """
        for eae in eae_records:
            if eae.transaction_type == "Expiration":
                self._handle_expiration(eae)
            elif eae.transaction_type in ["Exercise", "Assignment"]:
                self._handle_exercise_assignment(eae, trades)

    def _handle_expiration(self, eae: OptionEAECreate):
        """Closes an option lot and realizes the premium as a loss/gain."""
        # Find the open lot for this option
        lot = self._find_option_lot(eae)
        if not lot:
            return

        # For long lots (remaining_quantity > 0), cost_basis_total is positive cost.
        # Expiration at 0 proceeds -> PnL = 0 - cost_basis_total = -cost_basis_total.
        # For short lots (remaining_quantity < 0), cost_basis_total is positive premium received.
        # Expiration at 0 -> PnL = cost_basis_total.
        
        pnl = -lot.cost_basis_total
        if lot.remaining_quantity < 0:
            pnl = lot.cost_basis_total
        
        gain = Gain(
            sell_trade_id=None,
            buy_lot_id=lot.id,
            quantity_matched=lot.remaining_quantity,
            tax_year=eae.date.year,
            proceeds=Decimal("0"),
            cost_basis_matched=lot.cost_basis_total,
            realized_pnl=pnl,
            tax_pool="Termingeschäfte"
        )
        self.session.add(gain)
        lot.remaining_quantity = Decimal("0")
        self.session.flush()

    def _handle_exercise_assignment(self, eae: OptionEAECreate, trades: List[TradeSchema]):
        """Adjusts stock trade and closes option lot."""
        lot = self._find_option_lot(eae)
        if not lot:
            return

        # Find the corresponding stock trade in the transient list
        # Match criteria: same date, same underlying, quantity matches eae.quantity * multiplier
        # Also strike price should match trade_price of the stock trade (IBKR logs strike as price)
        target_qty = abs(eae.quantity * eae.multiplier)
        
        target_trade = None
        for t in trades:
            if (t.symbol == eae.underlying_symbol and 
                t.trade_date == eae.date and 
                abs(t.quantity) == target_qty and
                abs(t.trade_price - eae.strike) < Decimal("0.01")):
                target_trade = t
                break
        
        if not target_trade:
            # If not found in transient list, maybe it's already in DB? 
            # (Unlikely in standard pipeline flow)
            return

        # Transfer cost basis
        # If we were Long the option (cost_basis_total > 0):
        #   - Exercise Call: Adding premium to stock cost. (Stock quantity > 0, proceeds < 0)
        #     Adjustment: proceeds -= eae_cost_basis_in_currency (-15000 - 500 = -15500)
        #   - Exercise Put: Deducting premium from proceeds. (Stock quantity < 0, proceeds > 0)
        #     Adjustment: proceeds -= eae_cost_basis_in_currency (15000 - 500 = 14500)
        
        # If we were Short the option (cost_basis_total > 0, but it was premium RECEIVED):
        #   - Assign Call: Adding premium received to stock proceeds. (Stock quantity < 0, proceeds > 0)
        #     Adjustment: proceeds += eae_cost_basis_in_currency (15000 + 500 = 15500)
        #   - Assign Put: Deducting premium received from stock cost. (Stock quantity > 0, proceeds < 0)
        #     Adjustment: proceeds += eae_cost_basis_in_currency (-15000 + 500 = -14500)
        
        # Option premium in currency
        premium_in_currency = lot.cost_basis_total / eae.fx_rate_to_base
        
        if lot.remaining_quantity < 0:
            target_trade.proceeds += premium_in_currency
        else:
            target_trade.proceeds -= premium_in_currency
        # Let's verify:
        # Buy Stock (Exercise Call): Strike=100, Qty=1. Proceeds = -100. Premium = 5. New Proceeds = -105. Correct.
        # Sell Stock (Exercise Put): Strike=100, Qty=-1. Proceeds = 100. Premium = 5. New Proceeds = 95. Correct.
        # Sell Stock (Assign Call): Strike=100, Qty=-1. Proceeds = 100. Premium Received = -5 (lot cost is negative). New Proceeds = 105. Correct.
        # Buy Stock (Assign Put): Strike=100, Qty=1. Proceeds = -100. Premium Received = -5. New Proceeds = -95. Correct.

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
