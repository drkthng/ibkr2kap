import pytest
from decimal import Decimal
from datetime import date
from ibkr_tax.models.database import Account, Trade, FIFOLot, Gain
from ibkr_tax.services.fifo import FIFOEngine
from ibkr_tax.services.fifo_runner import FIFORunner
from ibkr_tax.services.option_engine import OptionEngine
from ibkr_tax.schemas.ibkr import OptionEAECreate, TradeSchema
from ibkr_tax.db.repository import import_trades

@pytest.fixture
def account(db_session):
    acc = Account(account_id="U123456", currency="EUR")
    db_session.add(acc)
    db_session.flush()
    return acc

def test_option_expiration_long(db_session, account):
    # Setup open option lot (Long Call)
    buy_trade = Trade(
        ib_trade_id="OPT_B1", account_id=account.id, asset_category="OPT",
        symbol="AAPL  230616C00150000", description="AAPL 150 Call",
        trade_date="2023-01-01", settle_date="2023-01-03",
        currency="USD", fx_rate_to_base=Decimal("1.0"),
        quantity=Decimal("1"), trade_price=Decimal("5"), proceeds=Decimal("-500"),
        buy_sell="BUY", open_close_indicator="O"
    )
    db_session.add(buy_trade)
    db_session.flush()
    FIFOEngine(db_session).process_trade(buy_trade)
    
    lot = db_session.query(FIFOLot).filter_by(trade_id=buy_trade.id).one()
    
    eae = OptionEAECreate(
        account_id="U123456", currency="USD", fx_rate_to_base=Decimal("1.0"),
        symbol="AAPL  230616C00150000", underlying_symbol="AAPL", strike=Decimal("150"),
        expiry=date(2023, 6, 16), put_call="C", date=date(2023, 6, 16),
        transaction_type="Expiration", quantity=Decimal("1"), multiplier=Decimal("100")
    )
    
    OptionEngine(db_session).apply_option_adjustments([eae])
    
    # Expiration creates a synthetic trade. We need to run FIFO to close the lot.
    FIFORunner(db_session).run_all()
    
    # Re-fetch lot
    lot = db_session.query(FIFOLot).filter_by(trade_id=buy_trade.id).one()
    assert lot.remaining_quantity == 0
    gain = db_session.query(Gain).filter_by(buy_lot_id=lot.id).one()
    assert gain.realized_pnl == Decimal("-500")
    assert gain.tax_pool == "Termingeschäfte"

def test_option_expiration_short(db_session, account):
    # Setup open option lot (Short Put)
    sell_trade = Trade(
        ib_trade_id="OPT_S1", account_id=account.id, asset_category="OPT",
        symbol="AAPL  230616P00150000", description="AAPL 150 Put",
        trade_date="2023-01-01", settle_date="2023-01-03",
        currency="USD", fx_rate_to_base=Decimal("1.0"),
        quantity=Decimal("-1"), trade_price=Decimal("5"), proceeds=Decimal("500"),
        buy_sell="SELL", open_close_indicator="O"
    )
    db_session.add(sell_trade)
    db_session.flush()
    FIFOEngine(db_session).process_trade(sell_trade)
    
    lot = db_session.query(FIFOLot).filter_by(trade_id=sell_trade.id).one()
    
    eae = OptionEAECreate(
        account_id="U123456", currency="USD", fx_rate_to_base=Decimal("1.0"),
        symbol="AAPL  230616P00150000", underlying_symbol="AAPL", strike=Decimal("150"),
        expiry=date(2023, 6, 16), put_call="P", date=date(2023, 6, 16),
        transaction_type="Expiration", quantity=Decimal("-1"), multiplier=Decimal("100")
    )
    
    OptionEngine(db_session).apply_option_adjustments([eae])
    
    FIFORunner(db_session).run_all()
    
    lot = db_session.query(FIFOLot).filter_by(trade_id=sell_trade.id).one()
    assert lot.remaining_quantity == 0
    gain = db_session.query(Gain).filter_by(buy_lot_id=lot.id).one()
    # For Short, proceeds was positive (500). Expiration means we keep it. PnL = 500.
    assert gain.realized_pnl == Decimal("500")

def test_call_exercise_long(db_session, account):
    # Long Call Exercise -> Add premium to stock cost
    buy_opt = Trade(
        ib_trade_id="OPT_B2", account_id=account.id, asset_category="OPT",
        symbol="AAPL Call", description="AAPL Call",
        trade_date="2023-01-01", settle_date="2023-01-03",
        currency="EUR", fx_rate_to_base=Decimal("1.0"),
        quantity=Decimal("1"), trade_price=Decimal("5"), proceeds=Decimal("-500"),
        buy_sell="BUY", open_close_indicator="O"
    )
    db_session.add(buy_opt)
    db_session.flush()
    FIFOEngine(db_session).process_trade(buy_opt)
    
    stock_trade = TradeSchema(
        ib_trade_id="STK_B1", account_id="U123456", asset_category="STK",
        symbol="AAPL", description="Apple", trade_date=date(2023, 6, 16),
        settle_date=date(2023, 6, 18), currency="EUR", fx_rate_to_base=Decimal("1.0"),
        quantity=Decimal("100"), trade_price=Decimal("150"), proceeds=Decimal("-15000"),
        buy_sell="BUY", open_close_indicator="O"
    )
    import_trades(db_session, [stock_trade])
    
    eae = OptionEAECreate(
        account_id="U123456", currency="EUR", fx_rate_to_base=Decimal("1.0"),
        symbol="AAPL Call", underlying_symbol="AAPL", strike=Decimal("150"),
        expiry=date(2023, 6, 16), put_call="C", date=date(2023, 6, 16),
        transaction_type="Exercise", quantity=Decimal("1"), multiplier=Decimal("100")
    )
    
    OptionEngine(db_session).apply_option_adjustments([eae])
    
    db_trade = db_session.query(Trade).filter_by(ib_trade_id="STK_B1").one()
    assert db_trade.proceeds == Decimal("-15500") # -15000 - 500
    assert db_session.query(FIFOLot).filter_by(symbol="AAPL Call").one().remaining_quantity == 0

def test_put_exercise_long(db_session, account):
    # Long Put Exercise -> Deduct premium from stock proceeds (Sell stock)
    buy_opt = Trade(
        ib_trade_id="OPT_B3", account_id=account.id, asset_category="OPT",
        symbol="AAPL Put", description="AAPL Put",
        trade_date="2023-01-01", settle_date="2023-01-03",
        currency="EUR", fx_rate_to_base=Decimal("1.0"),
        quantity=Decimal("1"), trade_price=Decimal("5"), proceeds=Decimal("-500"),
        buy_sell="BUY", open_close_indicator="O"
    )
    db_session.add(buy_opt)
    db_session.flush()
    FIFOEngine(db_session).process_trade(buy_opt)
    
    stock_trade = TradeSchema(
        ib_trade_id="STK_S1", account_id="U123456", asset_category="STK",
        symbol="AAPL", description="Apple", trade_date=date(2023, 6, 16),
        settle_date=date(2023, 6, 18), currency="EUR", fx_rate_to_base=Decimal("1.0"),
        quantity=Decimal("-100"), trade_price=Decimal("150"), proceeds=Decimal("15000"),
        buy_sell="SELL", open_close_indicator="C"
    )
    import_trades(db_session, [stock_trade])
    
    eae = OptionEAECreate(
        account_id="U123456", currency="EUR", fx_rate_to_base=Decimal("1.0"),
        symbol="AAPL Put", underlying_symbol="AAPL", strike=Decimal("150"),
        expiry=date(2023, 6, 16), put_call="P", date=date(2023, 6, 16),
        transaction_type="Exercise", quantity=Decimal("1"), multiplier=Decimal("100")
    )
    
    OptionEngine(db_session).apply_option_adjustments([eae])
    
    db_trade = db_session.query(Trade).filter_by(ib_trade_id="STK_S1").one()
    assert db_trade.proceeds == Decimal("14500") # 15000 - 500
    assert db_session.query(FIFOLot).filter_by(symbol="AAPL Put").one().remaining_quantity == 0

def test_call_assignment_short(db_session, account):
    # Short Call Assignment -> Add premium received to stock proceeds (Sell stock)
    sell_opt = Trade(
        ib_trade_id="OPT_S2", account_id=account.id, asset_category="OPT",
        symbol="AAPL Call Short", description="AAPL Call Short",
        trade_date="2023-01-01", settle_date="2023-01-03",
        currency="EUR", fx_rate_to_base=Decimal("1.0"),
        quantity=Decimal("-1"), trade_price=Decimal("5"), proceeds=Decimal("500"),
        buy_sell="SELL", open_close_indicator="O"
    )
    db_session.add(sell_opt)
    db_session.flush()
    FIFOEngine(db_session).process_trade(sell_opt)
    
    stock_trade = TradeSchema(
        ib_trade_id="STK_S2", account_id="U123456", asset_category="STK",
        symbol="AAPL", description="Apple", trade_date=date(2023, 6, 16),
        settle_date=date(2023, 6, 18), currency="EUR", fx_rate_to_base=Decimal("1.0"),
        quantity=Decimal("-100"), trade_price=Decimal("150"), proceeds=Decimal("15000"),
        buy_sell="SELL", open_close_indicator="C"
    )
    import_trades(db_session, [stock_trade])
    
    eae = OptionEAECreate(
        account_id="U123456", currency="EUR", fx_rate_to_base=Decimal("1.0"),
        symbol="AAPL Call Short", underlying_symbol="AAPL", strike=Decimal("150"),
        expiry=date(2023, 6, 16), put_call="C", date=date(2023, 6, 16),
        transaction_type="Assignment", quantity=Decimal("-1"), multiplier=Decimal("100")
    )
    
    OptionEngine(db_session).apply_option_adjustments([eae])
    
    db_trade = db_session.query(Trade).filter_by(ib_trade_id="STK_S2").one()
    assert db_trade.proceeds == Decimal("15500") # 15000 + 500
    assert db_session.query(FIFOLot).filter_by(symbol="AAPL Call Short").one().remaining_quantity == 0

def test_put_assignment_short(db_session, account):
    # Short Put Assignment -> Deduct premium received from stock cost (Buy stock)
    sell_opt = Trade(
        ib_trade_id="OPT_S3", account_id=account.id, asset_category="OPT",
        symbol="AAPL Put Short", description="AAPL Put Short",
        trade_date="2023-01-01", settle_date="2023-01-03",
        currency="EUR", fx_rate_to_base=Decimal("1.0"),
        quantity=Decimal("-1"), trade_price=Decimal("5"), proceeds=Decimal("500"),
        buy_sell="SELL", open_close_indicator="O"
    )
    db_session.add(sell_opt)
    db_session.flush()
    FIFOEngine(db_session).process_trade(sell_opt)
    
    stock_trade = TradeSchema(
        ib_trade_id="STK_B2", account_id="U123456", asset_category="STK",
        symbol="AAPL", description="Apple", trade_date=date(2023, 6, 16),
        settle_date=date(2023, 6, 18), currency="EUR", fx_rate_to_base=Decimal("1.0"),
        quantity=Decimal("100"), trade_price=Decimal("150"), proceeds=Decimal("-15000"),
        buy_sell="BUY", open_close_indicator="O"
    )
    import_trades(db_session, [stock_trade])
    
    eae = OptionEAECreate(
        account_id="U123456", currency="EUR", fx_rate_to_base=Decimal("1.0"),
        symbol="AAPL Put Short", underlying_symbol="AAPL", strike=Decimal("150"),
        expiry=date(2023, 6, 16), put_call="P", date=date(2023, 6, 16),
        transaction_type="Assignment", quantity=Decimal("-1"), multiplier=Decimal("100")
    )
    
    OptionEngine(db_session).apply_option_adjustments([eae])
    
    db_trade = db_session.query(Trade).filter_by(ib_trade_id="STK_B2").one()
    assert db_trade.proceeds == Decimal("-14500") # -15000 - (-500) = -14500
    assert db_session.query(FIFOLot).filter_by(symbol="AAPL Put Short").one().remaining_quantity == 0
