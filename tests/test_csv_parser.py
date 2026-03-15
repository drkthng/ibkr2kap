import pytest
from decimal import Decimal
from datetime import date
from ibkr_tax.services.csv_parser import CSVActivityParser


MOCK_CSV = """Account Information,Header,Account ID,Base Currency
Account Information,Data,U1234567,EUR
Trades,Header,Account ID,Asset Category,Symbol,Description,Trade Date,Settle Date Target,Currency,FX Rate To Base,Quantity,Trade Price,Proceeds,Taxes,Comm/Fee,Buy/Sell,Trade ID,Open/Close Indicator
Trades,Data,U1234567,STK,AAPL,APPLE INC,2024-01-15,2024-01-17,USD,0.92,10,180.00,-1800.00,0,-1.00,BUY,T123,O
Trades,Data,U1234567,STK,AAPL,APPLE INC,2024-01-20,2024-01-22,USD,0.92,-5,190.00,950.00,0,-1.00,SELL,T124,C
Dividends,Header,Account ID,Currency,Symbol,Description,Date/Time,Amount,FX Rate To Base,Settle Date,Report Date
Dividends,Data,U1234567,USD,AAPL,APPLE INC (CASH DIVIDEND),2024-02-01,10.00,0.91,2024-02-01,2024-02-01
Withholding Tax,Header,Account ID,Currency,Symbol,Description,Date/Time,Amount,FX Rate To Base,Settle Date,Report Date
Withholding Tax,Data,U1234567,USD,AAPL,APPLE INC (WITHHOLDING TAX),2024-02-01,-1.50,0.91,2024-02-01,2024-02-01
"""

def test_csv_parser_accounts():
    parser = CSVActivityParser(csv_content=MOCK_CSV)
    accounts = parser.get_accounts()
    assert len(accounts) == 1
    assert accounts[0].account_id == "U1234567"
    assert accounts[0].currency == "EUR"

def test_csv_parser_trades():
    parser = CSVActivityParser(csv_content=MOCK_CSV)
    trades = parser.get_trades()
    assert len(trades) == 2
    
    # Check BUY trade
    buy_trade = next(t for t in trades if t.buy_sell == "BUY")
    assert buy_trade.symbol == "AAPL"
    assert buy_trade.quantity == Decimal("10")
    assert buy_trade.trade_price == Decimal("180.00")
    assert buy_trade.trade_date == date(2024, 1, 15)
    assert buy_trade.settle_date == date(2024, 1, 17)
    assert buy_trade.ib_trade_id == "T123"

    # Check SELL trade
    sell_trade = next(t for t in trades if t.buy_sell == "SELL")
    assert sell_trade.symbol == "AAPL"
    assert sell_trade.quantity == Decimal("-5")
    assert sell_trade.trade_price == Decimal("190.00")
    assert sell_trade.proceeds == Decimal("950.00")

def test_csv_parser_cash_transactions():
    parser = CSVActivityParser(csv_content=MOCK_CSV)
    cts = parser.get_cash_transactions()
    assert len(cts) == 2
    
    div = next(c for c in cts if c.type == "Dividends")
    assert div.amount == Decimal("10.00")
    assert div.symbol == "AAPL"
    assert div.currency == "USD"
    
    wt = next(c for c in cts if c.type == "Withholding Tax")
    assert wt.amount == Decimal("-1.50")
    assert wt.symbol == "AAPL"

def test_csv_parser_parse_all():
    parser = CSVActivityParser(csv_content=MOCK_CSV)
    result = parser.parse_all()
    assert "accounts" in result
    assert "trades" in result
    assert "cash_transactions" in result
    assert len(result["accounts"]) == 1
    assert len(result["trades"]) == 2
    assert len(result["cash_transactions"]) == 2
