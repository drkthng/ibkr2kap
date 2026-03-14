import pytest
from decimal import Decimal
from datetime import date
from ibkr_tax.schemas.ibkr import AccountSchema, TradeSchema, CashTransactionSchema
from ibkr_tax.models.database import Trade, CashTransaction


def test_account_schema_valid():
    acc = AccountSchema(account_id="U1234567")
    assert acc.account_id == "U1234567"
    assert acc.currency == "EUR"

    acc2 = AccountSchema(account_id=" U7654321 ", currency="USD")
    assert acc2.account_id == "U7654321"  # Stripped
    assert acc2.currency == "USD"


def test_account_schema_invalid():
    with pytest.raises(ValueError):
        AccountSchema(account_id="", currency="EUR")
    with pytest.raises(ValueError):
        AccountSchema(account_id="U1", currency="TOOLONG")


def test_trade_schema_valid_buy():
    data = {
        "ib_trade_id": "TR-1",
        "account_id": "U1234567",
        "asset_category": "STK",
        "symbol": "AAPL",
        "description": "APPLE INC",
        "trade_date": "2023-01-01",
        "settle_date": "2023-01-03",
        "currency": "USD",
        "fx_rate_to_base": "0.93",
        "quantity": "100",
        "trade_price": "150.00",
        "proceeds": "-15000.00",
        "buy_sell": "BUY"
    }
    trade = TradeSchema(**data)
    assert trade.quantity == Decimal("100")
    assert trade.fx_rate_to_base == Decimal("0.93")
    assert trade.settle_date == date(2023, 1, 3)
    
    db_dict = trade.to_db_dict()
    assert "account_id" not in db_dict
    assert db_dict["settle_date"] == "2023-01-03"


def test_trade_schema_valid_sell():
    data = {
        "ib_trade_id": "TR-2",
        "account_id": "U1234567",
        "asset_category": "STK",
        "symbol": "AAPL",
        "description": "APPLE INC",
        "trade_date": "2023-02-01",
        "settle_date": "2023-02-03",
        "currency": "USD",
        "fx_rate_to_base": "0.94",
        "quantity": "-100",
        "trade_price": "160.00",
        "proceeds": "16000.00",
        "buy_sell": "SELL"
    }
    trade = TradeSchema(**data)
    assert trade.quantity == Decimal("-100")
    assert trade.buy_sell == "SELL"


def test_trade_schema_rejection_logic():
    base_data = {
        "ib_trade_id": "TR-1", "account_id": "U1", "asset_category": "STK",
        "symbol": "T", "description": "D", "trade_date": "2023-01-01",
        "settle_date": "2023-01-03", "currency": "USD", "fx_rate_to_base": "1.0",
        "quantity": "10", "trade_price": "100", "proceeds": "-1000", "buy_sell": "BUY"
    }

    # Settle date before trade date
    bad_dates = base_data.copy()
    bad_dates["settle_date"] = "2022-12-31"
    with pytest.raises(ValueError, match="settle_date cannot be before"):
        TradeSchema(**bad_dates)

    # BUY with negative quantity
    bad_sign = base_data.copy()
    bad_sign["quantity"] = "-10"
    with pytest.raises(ValueError, match="BUY trade must have positive quantity"):
        TradeSchema(**bad_sign)

    # SELL with positive quantity
    bad_sign_sell = base_data.copy()
    bad_sign_sell["buy_sell"] = "SELL"
    with pytest.raises(ValueError, match="SELL trade must have negative quantity"):
        TradeSchema(**bad_sign_sell)

    # Zero quantity
    zero_qty = base_data.copy()
    zero_qty["quantity"] = "0"
    with pytest.raises(ValueError, match="quantity cannot be zero"):
        TradeSchema(**zero_qty)

    # Float rejection
    float_data = base_data.copy()
    float_data["quantity"] = 10.0
    with pytest.raises(ValueError, match="Floats are not allowed"):
        TradeSchema(**float_data)


def test_cash_transaction_schema_valid():
    data = {
        "account_id": "U1234567",
        "symbol": "AAPL",
        "description": "CASH DIVIDEND",
        "date_time": "2023-05-01;202000",
        "settle_date": "2023-05-01",
        "amount": "24.00",
        "type": "Dividends",
        "currency": "USD",
        "fx_rate_to_base": "0.92",
        "report_date": "2023-05-01"
    }
    tx = CashTransactionSchema(**data)
    assert tx.amount == Decimal("24.00")
    assert tx.type == "Dividends"
    
    db_dict = tx.to_db_dict()
    assert db_dict["report_date"] == "2023-05-01"


def test_schema_model_roundtrip():
    # Trade Roundtrip
    t_data = {
        "ib_trade_id": "RT-1", "account_id": "U1", "asset_category": "STK",
        "symbol": "AAPL", "description": "D", "trade_date": "2023-01-01",
        "settle_date": "2023-01-03", "currency": "USD", "fx_rate_to_base": "1.0",
        "quantity": "10", "trade_price": "100", "proceeds": "-1000", "buy_sell": "BUY"
    }
    schema = TradeSchema(**t_data)
    db_dict = schema.to_db_dict()
    
    # In real use, account_id FK would be resolved. Here we test if db_dict matches model fields.
    # We can't fully instantiate Trade without account_id FK if we were in DB, 
    # but we can check if Trade model accepts the dict keys (except the FK).
    model = Trade(account_id=999, **db_dict)
    assert model.ib_trade_id == "RT-1"
    assert model.settle_date == "2023-01-03"
    assert model.quantity == Decimal("10")


    # CashTransaction Roundtrip
    c_data = {
        "account_id": "U1", "description": "Fees", "date_time": "2023-01-01",
        "settle_date": "2023-01-01", "amount": "-1.50", "type": "Other Fees",
        "currency": "USD", "fx_rate_to_base": "1.0", "report_date": "2023-01-01"
    }
    c_schema = CashTransactionSchema(**c_data)
    c_db_dict = c_schema.to_db_dict()
    c_model = CashTransaction(account_id=999, **c_db_dict)
    assert c_model.amount == Decimal("-1.50")
    assert c_model.type == "Other Fees"
