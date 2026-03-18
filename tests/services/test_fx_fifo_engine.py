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
    
    # 1. EUR -> USD Conversion (Acquisition of 1000 USD)
    # Sell EUR.USD: sell EUR, receive USD. 
    # proceeds = +1000 USD, quantity = -900 EUR (approx)
    # fx_rate_to_base = 0.9 (EUR/USD) -> No, fx_rate_to_base is USD/EUR? 
    # Let's say 1 USD = 0.9 EUR. So fx_rate_to_base=0.9.
    acq_usd = Trade(
        ib_trade_id="T1", account_id=account.id, asset_category="CASH", symbol="EUR.USD",
        description="FX", trade_date="2023-01-01", trade_price=Decimal("1.11"),
        settle_date="2023-01-01",
        currency="USD", fx_rate_to_base=Decimal("0.9"), quantity=Decimal("-1111.11"),
        proceeds=Decimal("1000"), ib_commission=Decimal("0"),
        buy_sell="SELL"
    )
    db_session.add(acq_usd)
    db_session.flush()
    
    # 2. USD -> EUR Conversion (Disposal of 500 USD)
    # Buy EUR.USD: buy EUR, pay USD. 
    # proceeds = -500 USD
    disp_usd = Trade(
        ib_trade_id="T2", account_id=account.id, asset_category="CASH", symbol="EUR.USD",
        description="FX", trade_date="2023-02-01", trade_price=Decimal("1.05"),
        settle_date="2023-02-01",
        currency="USD", fx_rate_to_base=Decimal("0.95"), quantity=Decimal("526.31"),
        proceeds=Decimal("-500"), ib_commission=Decimal("0"),
        buy_sell="BUY"
    )
    db_session.add(disp_usd)
    db_session.flush()
    
    engine.process_all_fx(account.id)
    
    # Verify Lot
    lot = db_session.query(FXFIFOLot).filter_by(account_id=account.id).first()
    assert lot.remaining_amount == Decimal("500")
    assert lot.cost_basis_per_unit_eur == Decimal("0.9")
    
    # Verify Gain
    gain = db_session.query(FXGain).filter_by(account_id=account.id).first()
    assert gain.amount_matched == Decimal("500")
    # PnL = 500 * (0.95 - 0.9) = 25 EUR
    assert gain.realized_pnl_eur == Decimal("25")
    assert gain.is_taxable_section_23 is True

def test_fx_non_taxable_gain_after_one_year(db_session, account):
    engine = FXFIFOEngine(db_session)
    
    acq = Trade(
        ib_trade_id="T1", account_id=account.id, asset_category="CASH", symbol="EUR.USD",
        description="FX", trade_date="2023-01-01", trade_price=Decimal("1.11"),
        settle_date="2023-01-01",
        currency="USD", fx_rate_to_base=Decimal("0.9"), quantity=Decimal("-1111.11"),
        proceeds=Decimal("1000"), ib_commission=Decimal("0"),
        buy_sell="SELL"
    )
    db_session.add(acq)
    
    disp = Trade(
        ib_trade_id="T2", account_id=account.id, asset_category="CASH", symbol="EUR.USD",
        description="FX", trade_date="2024-02-01", trade_price=Decimal("1.0"),
        settle_date="2024-02-01",
        currency="USD", fx_rate_to_base=Decimal("1.0"), quantity=Decimal("1000"),
        proceeds=Decimal("-1000"), ib_commission=Decimal("0"),
        buy_sell="BUY"
    )
    db_session.add(disp)
    db_session.flush()
    
    engine.process_all_fx(account.id)
    
    gain = db_session.query(FXGain).first()
    assert gain.is_taxable_section_23 is False
    assert gain.days_held > 365
    assert gain.realized_pnl_eur == Decimal("100")

def test_multiple_currencies(db_session, account):
    engine = FXFIFOEngine(db_session)
    
    # USD conversion
    db_session.add(Trade(
        ib_trade_id="T1", account_id=account.id, asset_category="CASH", symbol="EUR.USD",
        description="FX", trade_date="2023-01-01", trade_price=Decimal("1.11"),
        settle_date="2023-01-01", currency="USD", fx_rate_to_base=Decimal("0.9"), 
        quantity=Decimal("-111"), proceeds=Decimal("100"), buy_sell="SELL"
    ))
    # GBP conversion
    db_session.add(Trade(
        ib_trade_id="T2", account_id=account.id, asset_category="CASH", symbol="EUR.GBP",
        description="FX", trade_date="2023-01-01", trade_price=Decimal("0.9"),
        settle_date="2023-01-01", currency="GBP", fx_rate_to_base=Decimal("1.1"), 
        quantity=Decimal("-90"), proceeds=Decimal("100"), buy_sell="SELL"
    ))
    db_session.flush()
    
    engine.process_all_fx(account.id)
    
    lots = db_session.query(FXFIFOLot).all()
    assert len(lots) == 2
    currencies = [l.currency for l in lots]
    assert "USD" in currencies
    assert "GBP" in currencies

def test_dividends_and_stocks_ignored(db_session, account):
    engine = FXFIFOEngine(db_session)
    
    # Stock trade
    db_session.add(Trade(
        ib_trade_id="T1", account_id=account.id, asset_category="STK", symbol="AAPL",
        description="STK", trade_date="2023-01-01", trade_price=Decimal("100"),
        settle_date="2023-01-01", currency="USD", fx_rate_to_base=Decimal("0.9"), 
        quantity=Decimal("10"), proceeds=Decimal("-1000"), buy_sell="BUY"
    ))
    # Dividend
    db_session.add(CashTransaction(
        account_id=account.id, settle_date="2023-01-01", amount=Decimal("100"),
        type="Dividend", currency="USD", fx_rate_to_base=Decimal("0.9"), action_id="D1",
        description="Dividend", date_time="2023-01-01;000000", report_date="2023-01-01"
    ))
    db_session.flush()
    
    engine.process_all_fx(account.id)
    
    # Should be NO lots
    assert db_session.query(FXFIFOLot).count() == 0

def test_cross_currency_trade(db_session, account):
    engine = FXFIFOEngine(db_session)
    
    # BUY GBP.USD -> Buy GBP, Sell USD.
    # quantity = +1000 GBP
    # proceeds = -1200 USD
    # fx_rate_to_base (for USD) = 0.9
    cross = Trade(
        ib_trade_id="T1", account_id=account.id, asset_category="CASH", symbol="GBP.USD",
        description="FX", trade_date="2023-01-01", trade_price=Decimal("1.2"),
        settle_date="2023-01-01", currency="USD", fx_rate_to_base=Decimal("0.9"), 
        quantity=Decimal("1000"), proceeds=Decimal("-1200"), buy_sell="BUY"
    )
    db_session.add(cross)
    db_session.flush()
    
    engine.process_all_fx(account.id)
    
    # Should have 1 GBP lot (acquisition) and 0 USD lots (disposal with no pool)
    # Actually, disposal doesn't create a lot anymore.
    gbp_lot = db_session.query(FXFIFOLot).filter_by(currency="GBP").first()
    assert gbp_lot is not None
    assert gbp_lot.original_amount == Decimal("1000")
    # Base rate = price (1.2) * 0.9 = 1.08
    assert gbp_lot.cost_basis_per_unit_eur == Decimal("1.08")
    
    usd_lot = db_session.query(FXFIFOLot).filter_by(currency="USD").first()
    assert usd_lot is None
