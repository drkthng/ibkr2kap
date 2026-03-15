import pytest
import os
from unittest.mock import MagicMock
from decimal import Decimal
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from ibkr_tax.models.database import Base, Account, Trade, CashTransaction
from ibkr_tax.services.pipeline import run_import
from ibkr_tax.schemas.ibkr import AccountSchema, TradeSchema, CashTransactionSchema

@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

def test_run_import_xml_mocked(session, monkeypatch):
    """Test XML import with mocked parser to avoid dependency on actual files/ibflex in unit test."""
    mock_parser_instance = MagicMock()
    mock_parser_instance.parse_all.return_value = {
        "accounts": [AccountSchema(account_id="U123", currency="EUR")],
        "trades": [
            TradeSchema(
                ib_trade_id="T1", account_id="U123", asset_category="STK", symbol="AAPL",
                description="Apple", trade_date=date(2023, 1, 1), settle_date=date(2023, 1, 3),
                currency="USD", fx_rate_to_base=Decimal("0.9"), quantity=Decimal("10"),
                trade_price=Decimal("150"), proceeds=Decimal("-1500"), buy_sell="BUY",
                open_close_indicator="O"
            )
        ],
        "cash_transactions": []
    }
    
    # Patch the class in the pipeline module
    monkeypatch.setattr("ibkr_tax.services.pipeline.FlexXMLParser", lambda **kwargs: mock_parser_instance)

    result = run_import("dummy.xml", session, file_type="xml")
    
    assert result["status"] == "success"
    assert result["counts"]["accounts"]["inserted"] == 1
    assert result["counts"]["trades"]["inserted"] == 1
    assert session.query(Account).count() == 1
    assert session.query(Trade).count() == 1

def test_run_import_csv_mocked(session, monkeypatch):
    """Test CSV import with mocked parser."""
    mock_parser_instance = MagicMock()
    mock_parser_instance.parse_all.return_value = {
        "accounts": [AccountSchema(account_id="U456", currency="USD")],
        "trades": [],
        "cash_transactions": [
            CashTransactionSchema(
                account_id="U456", symbol="MSFT", description="Div", 
                date_time="2023-01-01 10:00:00", settle_date=date(2023, 1, 3),
                amount=Decimal("50"), type="Dividends", currency="USD",
                fx_rate_to_base=Decimal("1.0"), report_date=date(2023, 1, 1)
            )
        ]
    }
    
    monkeypatch.setattr("ibkr_tax.services.pipeline.CSVActivityParser", lambda **kwargs: mock_parser_instance)

    result = run_import("dummy.csv", session, file_type="csv")
    
    assert result["status"] == "success"
    assert result["counts"]["accounts"]["inserted"] == 1
    assert result["counts"]["cash_transactions"]["inserted"] == 1
    assert session.query(Account).count() == 1
    assert session.query(CashTransaction).count() == 1

def test_run_import_idempotency_mocked(session, monkeypatch):
    """Verify that running the import twice doesn't create duplicates."""
    mock_parser_instance = MagicMock()
    mock_data = {
        "accounts": [AccountSchema(account_id="U123", currency="EUR")],
        "trades": [],
        "cash_transactions": []
    }
    mock_parser_instance.parse_all.return_value = mock_data
    
    monkeypatch.setattr("ibkr_tax.services.pipeline.FlexXMLParser", lambda **kwargs: mock_parser_instance)

    # First run
    run_import("dummy.xml", session, file_type="xml")
    assert session.query(Account).count() == 1
    
    # Second run
    result = run_import("dummy.xml", session, file_type="xml")
    assert result["counts"]["accounts"]["inserted"] == 0
    assert session.query(Account).count() == 1
