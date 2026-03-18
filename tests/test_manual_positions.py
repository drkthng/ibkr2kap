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


# --- Integration tests (Plan 28.2) ---

def test_add_manual_position_repository(db_session, account):
    """Repository add + get functions should create and retrieve a ManualPosition."""
    from ibkr_tax.db.repository import add_manual_position, get_manual_positions

    mp = add_manual_position(
        db_session, account.id,
        symbol="MSFT", asset_category="STK",
        quantity=Decimal("200"), acquisition_date="2019-06-15",
        cost_basis_total_eur=Decimal("25000.0000"),
        description="Test Entry",
    )
    assert mp.id is not None

    positions = get_manual_positions(db_session, account.id)
    assert len(positions) == 1
    assert positions[0].symbol == "MSFT"
    assert positions[0].quantity == Decimal("200")


def test_delete_manual_position_repository(db_session, account):
    """Repository delete should remove the ManualPosition."""
    from ibkr_tax.db.repository import add_manual_position, delete_manual_position, get_manual_positions

    mp = add_manual_position(
        db_session, account.id,
        symbol="GOOG", asset_category="STK",
        quantity=Decimal("10"), acquisition_date="2018-01-10",
        cost_basis_total_eur=Decimal("10000.0000"),
    )
    assert delete_manual_position(db_session, mp.id) is True
    assert get_manual_positions(db_session, account.id) == []


def test_manual_position_eliminates_warning(db_session, account, manual_position):
    """A ManualPosition should prevent the 'missing cost basis' warning for covered sells."""
    # Sell 50 AAPL — but manual_position covers 100, so NO warning expected
    sell = Trade(
        ib_trade_id="SELL_WARN",
        account_id=account.id,
        asset_category="STK",
        symbol="AAPL",
        description="Apple Sell",
        trade_date="2023-03-01",
        settle_date="2023-03-03",
        currency="EUR",
        fx_rate_to_base=Decimal("1.0"),
        quantity=Decimal("-50"),
        trade_price=Decimal("170"),
        proceeds=Decimal("8500"),
        ib_commission=Decimal("-5"),
        taxes=Decimal("0"),
        buy_sell="SELL",
    )
    db_session.add(sell)
    db_session.flush()

    # Run FIFO to match sell against manual position
    runner = FIFORunner(db_session)
    runner.run_for_account(account.id)

    # Generate tax report — should have no missing cost basis warnings
    from ibkr_tax.services.tax_aggregator import TaxAggregatorService
    aggregator = TaxAggregatorService(db_session)
    report = aggregator.generate_report("U999", 2023)
    assert report.missing_cost_basis_warnings == []


def test_manual_position_as_sell_trade(db_session, account):
    """A manual position with buy_sell='SELL' should match against an existing BUY trade."""
    # 1. Add a BUY trade
    buy = Trade(
        ib_trade_id="BUY_FOR_MANUAL_SELL",
        account_id=account.id,
        asset_category="STK",
        symbol="TSLA",
        description="Tesla Buy",
        trade_date="2023-01-01",
        settle_date="2023-01-03",
        currency="EUR",
        fx_rate_to_base=Decimal("1.0"),
        quantity=Decimal("10"),
        trade_price=Decimal("100"),
        proceeds=Decimal("-1000"),
        ib_commission=Decimal("-5"),
        taxes=Decimal("0"),
        buy_sell="BUY",
    )
    db_session.add(buy)
    db_session.flush()

    # 2. Add a manual SELL position
    mp = ManualPosition(
        account_id=account.id,
        symbol="TSLA",
        asset_category="STK",
        quantity=Decimal("10"),
        acquisition_date="2023-02-01",
        buy_sell="SELL",
        open_close_indicator="C",
        proceeds=Decimal("1500"),
        ib_commission=Decimal("-5"),
        fx_rate_to_base=Decimal("1.0"),
        currency="EUR",
        description="Manual Sell"
    )
    db_session.add(mp)
    db_session.flush()

    # 3. Run FIFO
    runner = FIFORunner(db_session)
    runner.run_for_account(account.id)

    # 4. Verify Gain
    gains = db_session.query(Gain).all()
    assert len(gains) == 1
    gain = gains[0]
    assert gain.quantity_matched == Decimal("10")
    # net_proceeds = 1500 - 5 = 1495
    # cost_basis = 1000 + 5 = 1005
    # pnl = 1495 - 1005 = 490
    assert gain.realized_pnl == Decimal("490.0000")


def test_manual_position_category_mismatch(db_session, account):
    """FIFO should NOT match if asset_category differs, but SHOULD match if they are the same."""
    # 1. Add a BUY manual position with category 'STK'
    mp_stk = ManualPosition(
        account_id=account.id,
        symbol="MATCH_TEST",
        asset_category="STK",
        quantity=Decimal("10"),
        acquisition_date="2023-01-01",
        buy_sell="BUY",
        open_close_indicator="O",
        proceeds=Decimal("-100"),
        trade_price=Decimal("10"),
        fx_rate_to_base=Decimal("1.0"),
        currency="EUR"
    )
    db_session.add(mp_stk)
    
    # 2. Add a SELL trade with category 'OPT'
    sell_opt = Trade(
        ib_trade_id="SELL_OPT",
        account_id=account.id,
        asset_category="OPT",
        symbol="MATCH_TEST",
        description="Option Sell",
        trade_date="2023-02-01",
        settle_date="2023-02-02",
        currency="EUR",
        fx_rate_to_base=Decimal("1.0"),
        quantity=Decimal("10"),
        trade_price=Decimal("15"),
        proceeds=Decimal("150"),
        buy_sell="SELL",
    )
    db_session.add(sell_opt)
    db_session.flush()
    
    # 3. Run FIFO - should NOT match
    runner = FIFORunner(db_session)
    runner.run_for_account(account.id)
    
    gains = db_session.query(Gain).all()
    assert len(gains) == 0  # No match due to category mismatch
    
    # 4. Add a BUY manual position with category 'OPT' (correct match)
    mp_opt = ManualPosition(
        account_id=account.id,
        symbol="MATCH_TEST",
        asset_category="OPT",
        quantity=Decimal("10"),
        acquisition_date="2023-01-01",
        buy_sell="BUY",
        open_close_indicator="O",
        proceeds=Decimal("-100"),
        trade_price=Decimal("10"),
        fx_rate_to_base=Decimal("1.0"),
        currency="EUR"
    )
    db_session.add(mp_opt)
    db_session.flush()
    
    # 5. Run FIFO - should match mp_opt
    runner.run_for_account(account.id)
    
    gains = db_session.query(Gain).all()
    assert len(gains) == 1
    assert gains[0].quantity_matched == Decimal("10")


