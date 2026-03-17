import pytest
from decimal import Decimal
from ibkr_tax.models.database import Account, Trade, FIFOLot, Gain, ManualPosition
from ibkr_tax.services.fifo_runner import FIFORunner
from ibkr_tax.services.maintenance import MaintenanceService


@pytest.fixture
def account(db_session):
    acc = Account(account_id="U999", currency="EUR")
    db_session.add(acc)
    db_session.flush()
    return acc


@pytest.fixture
def manual_position(db_session, account):
    mp = ManualPosition(
        account_id=account.id,
        symbol="AAPL",
        asset_category="STK",
        quantity=Decimal("100"),
        acquisition_date="2020-01-03",
        cost_basis_total_eur=Decimal("10000.0000"),
        description="Manual Opening Position",
    )
    db_session.add(mp)
    db_session.flush()
    return mp


def test_manual_position_creates_fifo_lot(db_session, account, manual_position):
    """ManualPosition should produce exactly one FIFOLot with correct fields."""
    runner = FIFORunner(db_session)
    runner.run_for_account(account.id)

    lots = db_session.query(FIFOLot).filter(FIFOLot.manual_position_id == manual_position.id).all()
    assert len(lots) == 1

    lot = lots[0]
    assert lot.symbol == "AAPL"
    assert lot.asset_category == "STK"
    assert lot.settle_date == "2020-01-03"
    assert lot.original_quantity == Decimal("100")
    assert lot.remaining_quantity == Decimal("100")
    assert lot.cost_basis_total == Decimal("10000.0000")
    assert lot.cost_basis_per_share == Decimal("100.0000")
    assert lot.manual_position_id == manual_position.id
    assert lot.trade_id is None
    assert lot.transfer_id is None


def test_manual_position_resolves_sell(db_session, account, manual_position):
    """A sell trade should match against the manual position lot via FIFO."""
    # Add a SELL trade after the manual position date
    sell = Trade(
        ib_trade_id="SELL1",
        account_id=account.id,
        asset_category="STK",
        symbol="AAPL",
        description="Apple Sell",
        trade_date="2023-02-01",
        settle_date="2023-02-03",
        currency="EUR",
        fx_rate_to_base=Decimal("1.0"),
        quantity=Decimal("-50"),
        trade_price=Decimal("160"),
        proceeds=Decimal("8000"),
        ib_commission=Decimal("-5"),
        taxes=Decimal("0"),
        buy_sell="SELL",
    )
    db_session.add(sell)
    db_session.flush()

    runner = FIFORunner(db_session)
    runner.run_for_account(account.id)

    # Verify gain was created
    gains = db_session.query(Gain).all()
    assert len(gains) == 1
    gain = gains[0]
    assert gain.quantity_matched == Decimal("50")
    # proceeds_matched = 50 * (8000 - 5) / 50 = 7995 / 50 * 50 = 7995
    # cost_basis_matched = (50 / 100) * 10000 = 5000
    # pnl = 7995 - 5000 = 2995
    assert gain.realized_pnl == Decimal("2995.0000")

    # Verify FIFOLot remaining
    lot = db_session.query(FIFOLot).filter(FIFOLot.manual_position_id == manual_position.id).one()
    assert lot.remaining_quantity == Decimal("50")


def test_manual_position_idempotency(db_session, account, manual_position):
    """Running FIFORunner twice should not duplicate the manual position lot."""
    runner = FIFORunner(db_session)
    runner.run_for_account(account.id)
    runner.run_for_account(account.id)

    lots = db_session.query(FIFOLot).filter(FIFOLot.manual_position_id == manual_position.id).all()
    assert len(lots) == 1


def test_manual_position_interleaving_order(db_session, account, manual_position):
    """Manual position (2020) should be matched before a later BUY trade (2021) when selling."""
    # Add a BUY trade after the manual position
    buy = Trade(
        ib_trade_id="BUY1",
        account_id=account.id,
        asset_category="STK",
        symbol="AAPL",
        description="Apple Buy",
        trade_date="2021-01-01",
        settle_date="2021-01-05",
        currency="EUR",
        fx_rate_to_base=Decimal("1.0"),
        quantity=Decimal("50"),
        trade_price=Decimal("130"),
        proceeds=Decimal("-6500"),
        ib_commission=Decimal("-5"),
        taxes=Decimal("0"),
        buy_sell="BUY",
    )
    # Sell 120 shares — should consume 100 from manual (2020) then 20 from BUY (2021)
    sell = Trade(
        ib_trade_id="SELL2",
        account_id=account.id,
        asset_category="STK",
        symbol="AAPL",
        description="Apple Sell",
        trade_date="2023-06-01",
        settle_date="2023-06-05",
        currency="EUR",
        fx_rate_to_base=Decimal("1.0"),
        quantity=Decimal("-120"),
        trade_price=Decimal("170"),
        proceeds=Decimal("20400"),
        ib_commission=Decimal("-10"),
        taxes=Decimal("0"),
        buy_sell="SELL",
    )
    db_session.add_all([buy, sell])
    db_session.flush()

    runner = FIFORunner(db_session)
    runner.run_for_account(account.id)

    gains = db_session.query(Gain).order_by(Gain.id).all()
    # Should have 2 gain records: 100 matched from manual, 20 matched from buy
    assert len(gains) == 2
    assert gains[0].quantity_matched == Decimal("100")
    assert gains[1].quantity_matched == Decimal("20")

    # Manual position lot should be fully consumed
    mp_lot = db_session.query(FIFOLot).filter(FIFOLot.manual_position_id == manual_position.id).one()
    assert mp_lot.remaining_quantity == Decimal("0")


def test_maintenance_clears_manual_positions(db_session, account, manual_position):
    """MaintenanceService.reset_database() should clear all manual positions."""
    maint = MaintenanceService(db_session)
    maint.reset_database()

    count = db_session.query(ManualPosition).count()
    assert count == 0
