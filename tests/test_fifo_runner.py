import pytest
from decimal import Decimal
from ibkr_tax.models.database import Account, Trade, FIFOLot, Gain
from ibkr_tax.services.fifo_runner import FIFORunner

@pytest.fixture
def populated_db(db_session):
    # Setup two accounts
    acc1 = Account(account_id="U111", currency="EUR")
    acc2 = Account(account_id="U222", currency="EUR")
    db_session.add_all([acc1, acc2])
    db_session.flush()
    
    # acc1 trades: Buy 100, Sell 50
    t1 = Trade(ib_trade_id="T1", account_id=acc1.id, asset_category="STK", symbol="AAPL", 
               description="Apple", trade_date="2023-01-01", settle_date="2023-01-03", 
               currency="EUR", fx_rate_to_base=Decimal("1.0"), quantity=Decimal("100"), 
               trade_price=Decimal("150"), proceeds=Decimal("-15000"), ib_commission=Decimal("-5"), 
               buy_sell="BUY")
    t2 = Trade(ib_trade_id="T2", account_id=acc1.id, asset_category="STK", symbol="AAPL", 
               description="Apple", trade_date="2023-02-01", settle_date="2023-02-03", 
               currency="EUR", fx_rate_to_base=Decimal("1.0"), quantity=Decimal("-50"), 
               trade_price=Decimal("160"), proceeds=Decimal("8000"), ib_commission=Decimal("-5"), 
               buy_sell="SELL")
    
    # acc2 trades: Buy 200, Sell 200
    t3 = Trade(ib_trade_id="T3", account_id=acc2.id, asset_category="STK", symbol="TSLA", 
               description="Tesla", trade_date="2023-01-01", settle_date="2023-01-03", 
               currency="EUR", fx_rate_to_base=Decimal("1.0"), quantity=Decimal("200"), 
               trade_price=Decimal("200"), proceeds=Decimal("-40000"), ib_commission=Decimal("-10"), 
               buy_sell="BUY")
    t4 = Trade(ib_trade_id="T4", account_id=acc2.id, asset_category="STK", symbol="TSLA", 
               description="Tesla", trade_date="2023-03-01", settle_date="2023-03-03", 
               currency="EUR", fx_rate_to_base=Decimal("1.0"), quantity=Decimal("-200"), 
               trade_price=Decimal("210"), proceeds=Decimal("42000"), ib_commission=Decimal("-10"), 
               buy_sell="SELL")
    
    db_session.add_all([t1, t2, t3, t4])
    db_session.flush()
    return acc1, acc2

def test_runner_all_accounts(db_session, populated_db):
    acc1, acc2 = populated_db
    runner = FIFORunner(db_session)
    runner.run_all()
    
    # Verify acc1: 1 lot (50 remaining), 1 gain
    lots1 = db_session.query(FIFOLot).join(Trade).filter(Trade.account_id == acc1.id).all()
    assert len(lots1) == 1
    assert lots1[0].remaining_quantity == Decimal("50")
    
    gains1 = db_session.query(Gain).join(Trade, Gain.sell_trade_id == Trade.id).filter(Trade.account_id == acc1.id).all()
    assert len(gains1) == 1
    assert gains1[0].quantity_matched == Decimal("50")
    
    # Verify acc2: 1 lot (0 remaining), 1 gain
    lots2 = db_session.query(FIFOLot).join(Trade).filter(Trade.account_id == acc2.id).all()
    assert len(lots2) == 1
    assert lots2[0].remaining_quantity == Decimal("0")
    
    gains2 = db_session.query(Gain).join(Trade, Gain.sell_trade_id == Trade.id).filter(Trade.account_id == acc2.id).all()
    assert len(gains2) == 1
    assert gains2[0].quantity_matched == Decimal("200")

def test_runner_idempotency(db_session, populated_db):
    acc1, acc2 = populated_db
    runner = FIFORunner(db_session)
    
    # Run once
    runner.run_for_account(acc1.id)
    gains_count_1 = db_session.query(Gain).join(Trade, Gain.sell_trade_id == Trade.id).filter(Trade.account_id == acc1.id).count()
    assert gains_count_1 == 1
    
    # Run twice
    runner.run_for_account(acc1.id)
    gains_count_2 = db_session.query(Gain).join(Trade, Gain.sell_trade_id == Trade.id).filter(Trade.account_id == acc1.id).count()
    assert gains_count_2 == 1 # Should NOT increase
    
    # Check that lots are also not duplicated
    lots_count = db_session.query(FIFOLot).join(Trade).filter(Trade.account_id == acc1.id).count()
    assert lots_count == 1
