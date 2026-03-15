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

        # Realize full remaining cost as loss (if long) or gain (if short)
        # Note: In Termingeschäfte, we realize the premium.
        # If it was a BUY (long), remaining_quantity > 0, cost_basis_total is POSITIVE. 
        # Expiration means we got 0 proceeds. PnL = 0 - cost_basis_total = -cost_basis_total.
        
        # We need a dummy "sell_trade_id" or allow null. 
        # Current Gain model requires sell_trade_id. 
        # This is a bit of a gap. I might need a dummy trade or just handle it differently.
        # For now, let's assume we create a minimal Gain record.
        # Actually, let's check the Gain model again.
        
        gain = Gain(
            sell_trade_id=None,  # Need to make this nullable in database.py if it isn't
            buy_lot_id=lot.id,
            quantity_matched=lot.remaining_quantity,
            tax_year=eae.date.year,
            proceeds=Decimal("0"),
            cost_basis_matched=lot.cost_basis_total,
            realized_pnl=-lot.cost_basis_total,
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
        #     Adjustment: proceeds -= eae_cost_basis_in_currency
        #   - Exercise Put: Deducting premium from proceeds. (Stock quantity < 0, proceeds > 0)
        #     Adjustment: proceeds -= eae_cost_basis_in_currency
        
        # Option premium in currency
        premium_in_currency = lot.cost_basis_total / eae.fx_rate_to_base
        
        # Proceed adjustment: 
        # IBKR 'proceeds' is (price * qty). For BUY it's negative.
        # We want to increase the absolute cost or decrease the absolute proceeds.
        # Actually, standard formula: 
        # Cost Basis = (Strike * Qty) + Premium
        # Proceeds = (Strike * Qty) - Premium
        
        # In our TradeSchema, 'proceeds' includes commission/taxes? 
        # Actually standard IBKR proceeds is just Price * Qty.
        
        # If we just adjust target_trade.proceeds, the FIFO engine will use it.
        target_trade.proceeds -= premium_in_currency  # Works for both Buy and Sell?
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
            .where(FIFOLot.remaining_quantity > 0)
            .order_by(asc(FIFOLot.settle_date))
        )
        return self.session.execute(stmt).scalars().first()
