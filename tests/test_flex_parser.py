import pytest
from decimal import Decimal
from datetime import date
import os

from ibkr_tax.services.flex_parser import FlexXMLParser
from ibkr_tax.schemas.ibkr import TradeSchema, CashTransactionSchema

@pytest.fixture
def example_xml_path():
    # Use one of the real examples from the repo
    path = r"d:\Antigravity\IBKR2KAP\example\U7230673_20240101_20241231_AF_1434039_b9efd8fc4d9a876b70112f66fdb53969.xml"
    if not os.path.exists(path):
        pytest.skip(f"Example XML not found at {path}")
    return path

def test_flex_parser_basics(example_xml_path):
    parser = FlexXMLParser(xml_path=example_xml_path)
    results = parser.parse_all()
    
    accounts = results["accounts"]
    trades = results["trades"]
    cash_transactions = results["cash_transactions"]
    
    assert len(accounts) > 0
    assert accounts[0].account_id == "U7230673"
    
    assert len(trades) > 0
    # Check a specific trade if possible or just general validation
    for trade in trades:
        assert isinstance(trade, TradeSchema)
        assert trade.account_id == "U7230673"
        assert isinstance(trade.quantity, Decimal)
        assert isinstance(trade.trade_date, date)

    assert len(cash_transactions) > 0
    for ct in cash_transactions:
        assert isinstance(ct, CashTransactionSchema)
        assert ct.account_id == "U7230673"
        assert isinstance(ct.amount, Decimal)
        # Verify action_id was extracted (it should be for some transactions in this file)
        # The first few CashTransactions in the file had actionID
        if ct.type == "Withholding Tax":
             assert ct.action_id is not None

def test_flex_parser_withholding_tax_action_id(example_xml_path):
    parser = FlexXMLParser(xml_path=example_xml_path)
    cts = parser.get_cash_transactions()
    
    # Filter for first Withholding Tax in the file
    wt_tx = next(tx for tx in cts if tx.type == "Withholding Tax" and tx.amount == Decimal("-0.2"))
    assert wt_tx.action_id == "129946510"

def test_flex_parser_trade_mapping(example_xml_path):
    parser = FlexXMLParser(xml_path=example_xml_path)
    trades = parser.get_trades()
    
    # Check first trade (or any trade)
    trade = trades[0]
    assert trade.ib_trade_id != ""
    assert trade.asset_category in ["STK", "OPT", "FUT", "CASH", "WAR"]
    assert trade.buy_sell in ["BUY", "SELL"]

def test_flex_parser_error_on_missing_input():
    with pytest.raises(ValueError, match="Either xml_content or xml_path must be provided"):
        FlexXMLParser()
