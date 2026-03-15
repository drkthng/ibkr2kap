from datetime import date
from decimal import Decimal
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from ibkr_tax.models.database import Base, Account, Trade, CashTransaction
from ibkr_tax.schemas.ibkr import AccountSchema, TradeSchema, CashTransactionSchema
from ibkr_tax.db.repository import import_accounts, import_trades, import_cash_transactions

@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

def test_import_accounts(session):
    acc1 = AccountSchema(account_id="U123456", currency="EUR")
    acc2 = AccountSchema(account_id="U789012", currency="USD")
    
    # First insert
    inserted = import_accounts(session, [acc1, acc2])
    assert inserted == 2
    assert session.query(Account).count() == 2
    
    # Duplicate insert
    inserted2 = import_accounts(session, [acc1])
    assert inserted2 == 0
    assert session.query(Account).count() == 2

def test_import_trades(session):
    # Setup account first
    acc = AccountSchema(account_id="U123456", currency="EUR")
    import_accounts(session, [acc])
    
    trade1 = TradeSchema(
        ib_trade_id="TR1",
        account_id="U123456",
        asset_category="STK",
        symbol="AAPL",
        description="APPLE INC",
        trade_date=date(2023, 1, 1),
        settle_date=date(2023, 1, 3),
        currency="USD",
        fx_rate_to_base=Decimal("0.9"),
        quantity=Decimal("10"),
        trade_price=Decimal("150.0"),
        proceeds=Decimal("-1500.0"),
        buy_sell="BUY",
        open_close_indicator="O"
    )
    
    # First insert
    inserted = import_trades(session, [trade1])
    assert inserted == 1
    assert session.query(Trade).count() == 1
    
    # Duplicate insert
    inserted2 = import_trades(session, [trade1])
    assert inserted2 == 0
    assert session.query(Trade).count() == 1
    
def test_import_cash_transactions(session):
    acc = AccountSchema(account_id="U123456", currency="EUR")
    import_accounts(session, [acc])
    
    cash1 = CashTransactionSchema(
        account_id="U123456",
        description="DIVIDEND",
        date_time="2023-01-01 10:00:00",
        settle_date=date(2023, 1, 3),
        amount=Decimal("10.50"),
        type="Dividends",
        currency="USD",
        fx_rate_to_base=Decimal("0.9"),
        report_date=date(2023, 1, 1)
    )
    
    cash2 = CashTransactionSchema(
        account_id="U123456",
        description="Tax",
        date_time="2023-01-01 10:00:00",
        settle_date=date(2023, 1, 3),
        amount=Decimal("-2.50"),
        type="Withholding Tax",
        currency="USD",
        fx_rate_to_base=Decimal("0.9"),
        action_id="123456",
        report_date=date(2023, 1, 1)
    )
    
    # First insert
    inserted = import_cash_transactions(session, [cash1, cash2])
    assert inserted == 2
    assert session.query(CashTransaction).count() == 2
    
    # Duplicate insert
    inserted2 = import_cash_transactions(session, [cash1, cash2])
    assert inserted2 == 0
    assert session.query(CashTransaction).count() == 2
