import pytest
from decimal import Decimal
from datetime import date
from pydantic import ValidationError
from ibkr_tax.models.database import Account, Trade, FIFOLot
from ibkr_tax.services.corporate_actions import CorporateActionEngine
from ibkr_tax.schemas.ibkr import CorporateActionSchema

@pytest.fixture
def account(db_session):
    acc = Account(account_id="U123456", currency="EUR")
    db_session.add(acc)
    db_session.flush()
    return acc

def test_forward_split_4_to_1(db_session, account):
    # Buy 10 shares at $100 -> $1000 cost
    lot = FIFOLot(
        trade_id=1, asset_category="STK", symbol="AAPL",
        settle_date="2023-01-01", original_quantity=Decimal("10"),
        remaining_quantity=Decimal("10"), cost_basis_total=Decimal("1000"),
        cost_basis_per_share=Decimal("100")
    )
    db_session.add(lot)
    db_session.flush()

    action = CorporateActionSchema(
        account_id="U123456", symbol="AAPL", action_type="StockSplit",
        date=date(2023, 6, 1), ratio=Decimal("4"), description="4:1 Split"
    )

    CorporateActionEngine(db_session).apply_stock_split(action)

    db_session.refresh(lot)
    assert lot.original_quantity == Decimal("40")
    assert lot.remaining_quantity == Decimal("40")
    assert lot.cost_basis_per_share == Decimal("25")
    assert lot.cost_basis_total == Decimal("1000")

def test_reverse_split_1_to_10(db_session, account):
    # Buy 1000 shares at $1 -> $1000 cost
    lot = FIFOLot(
        trade_id=2, asset_category="STK", symbol="PENY",
        settle_date="2023-01-01", original_quantity=Decimal("1000"),
        remaining_quantity=Decimal("1000"), cost_basis_total=Decimal("1000"),
        cost_basis_per_share=Decimal("1")
    )
    db_session.add(lot)
    db_session.flush()

    action = CorporateActionSchema(
        account_id="U123456", symbol="PENY", action_type="ReverseStockSplit",
        date=date(2023, 6, 1), ratio=Decimal("0.1"), description="1:10 Reverse Split"
    )

    CorporateActionEngine(db_session).apply_stock_split(action)

    db_session.refresh(lot)
    assert lot.original_quantity == Decimal("100")
    assert lot.remaining_quantity == Decimal("100")
    assert lot.cost_basis_per_share == Decimal("10")
    assert lot.cost_basis_total == Decimal("1000")

def test_split_only_affects_target_symbol(db_session, account):
    aapl = FIFOLot(
        trade_id=3, asset_category="STK", symbol="AAPL",
        settle_date="2023-01-01", original_quantity=Decimal("10"),
        remaining_quantity=Decimal("10"), cost_basis_total=Decimal("1000"),
        cost_basis_per_share=Decimal("100")
    )
    msft = FIFOLot(
        trade_id=4, asset_category="STK", symbol="MSFT",
        settle_date="2023-01-01", original_quantity=Decimal("10"),
        remaining_quantity=Decimal("10"), cost_basis_total=Decimal("1000"),
        cost_basis_per_share=Decimal("100")
    )
    db_session.add_all([aapl, msft])
    db_session.flush()

    action = CorporateActionSchema(
        account_id="U123456", symbol="AAPL", action_type="StockSplit",
        date=date(2023, 6, 1), ratio=Decimal("2"), description="2:1 Split"
    )

    CorporateActionEngine(db_session).apply_stock_split(action)

    db_session.refresh(aapl)
    db_session.refresh(msft)
    assert aapl.remaining_quantity == Decimal("20")
    assert msft.remaining_quantity == Decimal("10") # Untouched

def test_split_only_affects_open_lots(db_session, account):
    # Partial lot: 10 original, 5 remaining
    lot = FIFOLot(
        trade_id=5, asset_category="STK", symbol="TSLA",
        settle_date="2023-01-01", original_quantity=Decimal("10"),
        remaining_quantity=Decimal("5"), cost_basis_total=Decimal("1000"),
        cost_basis_per_share=Decimal("100")
    )
    db_session.add(lot)
    db_session.flush()

    action = CorporateActionSchema(
        account_id="U123456", symbol="TSLA", action_type="StockSplit",
        date=date(2023, 6, 1), ratio=Decimal("2"), description="2:1 Split"
    )

    CorporateActionEngine(db_session).apply_stock_split(action)

    db_session.refresh(lot)
    assert lot.original_quantity == Decimal("20")
    assert lot.remaining_quantity == Decimal("10")
    assert lot.cost_basis_total == Decimal("1000")

def test_split_fully_closed_lot_untouched(db_session, account):
    lot = FIFOLot(
        trade_id=6, asset_category="STK", symbol="META",
        settle_date="2023-01-01", original_quantity=Decimal("10"),
        remaining_quantity=Decimal("0"), cost_basis_total=Decimal("1000"),
        cost_basis_per_share=Decimal("100")
    )
    db_session.add(lot)
    db_session.flush()

    action = CorporateActionSchema(
        account_id="U123456", symbol="META", action_type="StockSplit",
        date=date(2023, 6, 1), ratio=Decimal("2"), description="2:1 Split"
    )

    CorporateActionEngine(db_session).apply_stock_split(action)

    db_session.refresh(lot)
    assert lot.original_quantity == Decimal("10") # Untouched
    assert lot.remaining_quantity == Decimal("0")

def test_schema_rejects_float():
    with pytest.raises(ValidationError, match="Floats are not allowed"):
        CorporateActionSchema(
            account_id="U123456", symbol="AAPL", action_type="StockSplit",
            date=date(2023, 6, 1), ratio=2.0, description="Float ratio"
        )

def test_schema_rejects_zero_ratio():
    with pytest.raises(ValidationError, match="greater than 0"):
        CorporateActionSchema(
            account_id="U123456", symbol="AAPL", action_type="StockSplit",
            date=date(2023, 6, 1), ratio=0, description="Zero ratio"
        )
