import pytest
from decimal import Decimal
from ibkr_tax.models.database import Account, Trade, FIFOLot, Gain
from ibkr_tax.services.fifo import FIFOEngine

@pytest.fixture
def account(db_session):
    acc = Account(account_id="U123456", currency="EUR")
    db_session.add(acc)
    db_session.flush()
    return acc

def test_basic_fifo_matching(db_session, account):
    engine = FIFOEngine(db_session)
    
    # 1. Buy 100 AAPL at 150
    buy_trade = Trade(
        ib_trade_id="B1",
        account_id=account.id,
        asset_category="STK",
        symbol="AAPL",
        description="Apple Inc",
        trade_date="2023-01-01",
        settle_date="2023-01-03",
        currency="USD",
        fx_rate_to_base=Decimal("0.9"), # 1 USD = 0.9 EUR
        quantity=Decimal("100"),
        trade_price=Decimal("150"),
        proceeds=Decimal("-15000"),
        ib_commission=Decimal("-5"),
        buy_sell="BUY",
        open_close_indicator="O"
    )
    db_session.add(buy_trade)
    db_session.flush()
    
    engine.process_trade(buy_trade)
    
    lot = db_session.query(FIFOLot).filter_by(trade_id=buy_trade.id).first()
    assert lot is not None
    assert lot.remaining_quantity == Decimal("100")
    # Cost = (15000 + 5) * 0.9 = 15005 * 0.9 = 13504.5
    assert lot.cost_basis_total == Decimal("13504.5")

    # 2. Sell 100 AAPL at 160
    sell_trade = Trade(
        ib_trade_id="S1",
        account_id=account.id,
        asset_category="STK",
        symbol="AAPL",
        description="Apple Inc",
        trade_date="2023-02-01",
        settle_date="2023-02-03",
        currency="USD",
        fx_rate_to_base=Decimal("0.95"), # 1 USD = 0.95 EUR
        quantity=Decimal("-100"),
        trade_price=Decimal("160"),
        proceeds=Decimal("16000"),
        ib_commission=Decimal("-5"),
        buy_sell="SELL",
        open_close_indicator="C"
    )
    db_session.add(sell_trade)
    db_session.flush()
    
    engine.process_trade(sell_trade)
    
    db_session.refresh(lot)
    assert lot.remaining_quantity == Decimal("0")
    
    gain = db_session.query(Gain).filter_by(sell_trade_id=sell_trade.id).first()
    assert gain is not None
    assert gain.quantity_matched == Decimal("100")
    # Proceeds (EUR) = (16000 - 5) * 0.95 = 15995 * 0.95 = 15195.25
    assert gain.proceeds == Decimal("15195.25")
    assert gain.cost_basis_matched == Decimal("13504.5")
    assert gain.realized_pnl == Decimal("15195.25") - Decimal("13504.5")

def test_multiple_buys_one_sell(db_session, account):
    engine = FIFOEngine(db_session)
    
    # Buy 50 at 100 (Settle T1)
    b1 = Trade(ib_trade_id="B1", account_id=account.id, asset_category="STK", symbol="MSFT", 
               description="MSFT", trade_date="2023-01-01", settle_date="2023-01-03", 
               currency="EUR", fx_rate_to_base=Decimal("1.0"), quantity=Decimal("50"), 
               trade_price=Decimal("100"), proceeds=Decimal("-5000"), ib_commission=Decimal("-1"), 
               buy_sell="BUY")
    # Buy 50 at 110 (Settle T2)
    b2 = Trade(ib_trade_id="B2", account_id=account.id, asset_category="STK", symbol="MSFT", 
               description="MSFT", trade_date="2023-01-05", settle_date="2023-01-07", 
               currency="EUR", fx_rate_to_base=Decimal("1.0"), quantity=Decimal("50"), 
               trade_price=Decimal("110"), proceeds=Decimal("-5500"), ib_commission=Decimal("-1"), 
               buy_sell="BUY")
    
    db_session.add_all([b1, b2])
    db_session.flush()
    engine.process_trade(b1)
    engine.process_trade(b2)
    
    # Sell 75 at 120
    s1 = Trade(ib_trade_id="S1", account_id=account.id, asset_category="STK", symbol="MSFT", 
               description="MSFT", trade_date="2023-01-10", settle_date="2023-01-12", 
               currency="EUR", fx_rate_to_base=Decimal("1.0"), quantity=Decimal("-75"), 
               trade_price=Decimal("120"), proceeds=Decimal("9000"), ib_commission=Decimal("-2"), 
               buy_sell="SELL")
    db_session.add(s1)
    db_session.flush()
    engine.process_trade(s1)
    
    gains = db_session.query(Gain).filter_by(sell_trade_id=s1.id).order_by(Gain.id).all()
    assert len(gains) == 2
    
    # First match: 50 from B1
    assert gains[0].quantity_matched == Decimal("50")
    assert gains[0].cost_basis_matched == Decimal("5001")
    
    # Second match: 25 from B2
    assert gains[1].quantity_matched == Decimal("25")
    # Cost basis B2 total = 5501. For 25 shares (half of 50) = 2750.5
    assert gains[1].cost_basis_matched == Decimal("2750.5")
    
    # Check remaining lots
    l1 = db_session.query(FIFOLot).filter_by(trade_id=b1.id).one()
    l2 = db_session.query(FIFOLot).filter_by(trade_id=b2.id).one()
    assert l1.remaining_quantity == 0
    assert l2.remaining_quantity == 25

def test_fractional_shares(db_session, account):
    # Test high precision decimals
    engine = FIFOEngine(db_session)
    
    b1 = Trade(ib_trade_id="B1", account_id=account.id, asset_category="STK", symbol="FRACT", 
               description="FRACT", trade_date="2023-01-01", settle_date="2023-01-03", 
               currency="EUR", fx_rate_to_base=Decimal("1.0"), quantity=Decimal("0.1234"), 
               trade_price=Decimal("1000"), proceeds=Decimal("-123.4"), ib_commission=Decimal("0.05"), 
               buy_sell="BUY")
    db_session.add(b1)
    db_session.flush()
    engine.process_trade(b1)
    
    s1 = Trade(ib_trade_id="S1", account_id=account.id, asset_category="STK", symbol="FRACT", 
               description="FRACT", trade_date="2023-01-05", settle_date="2023-01-07", 
               currency="EUR", fx_rate_to_base=Decimal("1.0"), quantity=Decimal("-0.0617"), 
               trade_price=Decimal("2000"), proceeds=Decimal("123.4"), ib_commission=Decimal("0.05"), 
               buy_sell="SELL")
    db_session.add(s1)
    db_session.flush()
    engine.process_trade(s1)
    
    gain = db_session.query(Gain).filter_by(sell_trade_id=s1.id).one()
    assert gain.quantity_matched == Decimal("0.0617")
    # 0.0617 is exactly half of 0.1234
    # Total cost = 123.4 + 0.05 = 123.45
    # Matched cost = 123.45 / 2 = 61.725
    assert gain.cost_basis_matched == Decimal("61.725")
