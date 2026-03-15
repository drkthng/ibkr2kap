import pytest
from decimal import Decimal
from ibkr_tax.models.database import Account, Trade, CashTransaction, FXFIFOLot, FXGain
from ibkr_tax.services.fx_fifo_engine import FXFIFOEngine

@pytest.fixture
def account(db_session):
    acc = Account(account_id="U_FX_TEST", currency="EUR")
    db_session.add(acc)
    db_session.flush()
    return acc

def test_fx_taxable_gain_within_year(db_session, account):
    engine = FXFIFOEngine(db_session)
    
    # 1. Sell Stock -> Acquisition of USD (1000 USD)
    # Acquisition 2023-01-01 at 0.9 EUR/USD
    buy_stock_proceeds = Trade(
        ib_trade_id="T1", account_id=account.id, asset_category="STK", symbol="AAPL",
        description="AAPL", trade_date="2023-01-01", settle_date="2023-01-01",
        currency="USD", fx_rate_to_base=Decimal("0.9"), quantity=Decimal("-10"),
        trade_price=Decimal("100"), proceeds=Decimal("1000"), ib_commission=Decimal("0"),
        buy_sell="SELL"
    )
    db_session.add(buy_stock_proceeds)
    db_session.flush()
    
    # 2. Buy Stock with USD -> Disposal of USD (500 USD)
    # Disposal 2023-02-01 at 0.95 EUR/USD (USD became more valuable)
    sell_fx_for_stock = Trade(
        ib_trade_id="T2", account_id=account.id, asset_category="STK", symbol="MSFT",
        description="MSFT", trade_date="2023-02-01", settle_date="2023-02-01",
        currency="USD", fx_rate_to_base=Decimal("0.95"), quantity=Decimal("5"),
        trade_price=Decimal("100"), proceeds=Decimal("-500"), ib_commission=Decimal("0"),
        buy_sell="BUY"
    )
    db_session.add(sell_fx_for_stock)
    db_session.flush()
    
    engine.process_all_fx(account.id)
    
    # Verify Lot
    lot = db_session.query(FXFIFOLot).filter_by(account_id=account.id).first()
    assert lot.remaining_amount == Decimal("500")
    assert lot.cost_basis_per_unit_eur == Decimal("0.9")
    
    # Verify Gain
    gain = db_session.query(FXGain).filter_by(account_id=account.id).first()
    assert gain.amount_matched == Decimal("500")
    # Cost = 500 * 0.9 = 450 EUR
    # Proceeds = 500 * 0.95 = 475 EUR
    # PnL = 25 EUR
    assert gain.realized_pnl_eur == Decimal("25")
    assert gain.days_held == 31
    assert gain.is_taxable_section_23 is True

def test_fx_non_taxable_gain_after_one_year(db_session, account):
    engine = FXFIFOEngine(db_session)
    
    # Acquisition 2023-01-01
    acq = CashTransaction(
        account_id=account.id, symbol=None, description="Deposit USD",
        date_time="2023-01-01;000000", settle_date="2023-01-01",
        amount=Decimal("1000"), type="Other", currency="USD",
        fx_rate_to_base=Decimal("0.9"), action_id="D1", report_date="2023-01-01"
    )
    db_session.add(acq)
    
    # Disposal 2024-02-01 (> 365 days)
    disp = CashTransaction(
        account_id=account.id, symbol=None, description="Withdraw USD",
        date_time="2024-02-01;000000", settle_date="2024-02-01",
        amount=Decimal("-1000"), type="Other", currency="USD",
        fx_rate_to_base=Decimal("1.0"), action_id="W1", report_date="2024-02-01"
    )
    db_session.add(disp)
    db_session.flush()
    
    engine.process_all_fx(account.id)
    
    gain = db_session.query(FXGain).first()
    assert gain.is_taxable_section_23 is False
    assert gain.days_held > 365
    # PnL = 1000 * (1.0 - 0.9) = 100 EUR
    assert gain.realized_pnl_eur == Decimal("100")

def test_multiple_currencies(db_session, account):
    engine = FXFIFOEngine(db_session)
    
    # USD
    db_session.add(CashTransaction(
        account_id=account.id, symbol=None, description="Deposit USD",
        date_time="2023-01-01;000000", settle_date="2023-01-01",
        amount=Decimal("100"), type="Other", currency="USD",
        fx_rate_to_base=Decimal("0.9"), action_id="USD1", report_date="2023-01-01"
    ))
    # GBP
    db_session.add(CashTransaction(
        account_id=account.id, symbol=None, description="Deposit GBP",
        date_time="2023-01-01;000000", settle_date="2023-01-01",
        amount=Decimal("100"), type="Other", currency="GBP",
        fx_rate_to_base=Decimal("1.1"), action_id="GBP1", report_date="2023-01-01"
    ))
    db_session.flush()
    
    engine.process_all_fx(account.id)
    
    lots = db_session.query(FXFIFOLot).all()
    assert len(lots) == 2
    currencies = [l.currency for l in lots]
    assert "USD" in currencies
    assert "GBP" in currencies
