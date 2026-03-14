from decimal import Decimal
from ibkr_tax.db.engine import get_engine, init_db
from ibkr_tax.models.database import Base, Account, Trade, Dividend, FIFOLot, Gain

def test_db_initialization():
    """Tests if the database can be initialized without errors."""
    engine = get_engine("sqlite:///:memory:")
    init_db(engine, Base.metadata)
    assert engine is not None

def test_full_schema_and_relationships(db_session):
    """Tests if all models can be saved and retrieved with correct relationships."""
    # 1. Create Account
    account = Account(account_id="U1234567", currency="EUR")
    db_session.add(account)
    db_session.flush()

    # 2. Create Trade (BUY)
    trade_buy = Trade(
        account_id=account.id,
        asset_category="STK",
        symbol="AAPL",
        trade_date="2023-01-01",
        settle_date="2023-01-03",
        quantity=Decimal("100"),
        trade_price=Decimal("150.00"),
        ib_commission=Decimal("1.00"),
        buy_sell="BUY"
    )
    db_session.add(trade_buy)
    db_session.flush()

    # 3. Create FIFOLot from the trade
    lot = FIFOLot(
        trade_id=trade_buy.id,
        asset_category="STK",
        symbol="AAPL",
        settle_date="2023-01-03",
        original_quantity=Decimal("100"),
        remaining_quantity=Decimal("100"),
        cost_basis_total=Decimal("15001.00"),
        cost_basis_per_share=Decimal("150.01")
    )
    db_session.add(lot)
    db_session.flush()

    # 4. Create Trade (SELL)
    trade_sell = Trade(
        account_id=account.id,
        asset_category="STK",
        symbol="AAPL",
        trade_date="2023-02-01",
        settle_date="2023-02-03",
        quantity=Decimal("-100"),
        trade_price=Decimal("160.00"),
        ib_commission=Decimal("1.00"),
        buy_sell="SELL"
    )
    db_session.add(trade_sell)
    db_session.flush()

    # 5. Create Gain
    gain = Gain(
        sell_trade_id=trade_sell.id,
        buy_lot_id=lot.id,
        quantity_matched=Decimal("100"),
        tax_year=2023,
        proceeds=Decimal("15999.00"),
        cost_basis_matched=Decimal("15001.00"),
        realized_pnl=Decimal("998.00"),
        tax_pool="Aktien"
    )
    db_session.add(gain)

    # 6. Create Dividend
    dividend = Dividend(
        account_id=account.id,
        symbol="AAPL",
        pay_date="2023-05-01",
        gross_rate=Decimal("0.24"),
        gross_amount=Decimal("24.00"),
        withholding_tax=Decimal("3.60"),
        currency="USD"
    )
    db_session.add(dividend)
    
    db_session.commit()

    # Verification
    retrieved_acc = db_session.query(Account).filter_by(account_id="U1234567").first()
    assert retrieved_acc is not None
    assert len(retrieved_acc.trades) == 2
    assert len(retrieved_acc.dividends) == 1

    retrieved_lot = db_session.query(FIFOLot).filter_by(symbol="AAPL").first()
    assert retrieved_lot.remaining_quantity == Decimal("100")
    assert retrieved_lot.trade.trade_date == "2023-01-01"

    retrieved_gain = db_session.query(Gain).first()
    assert retrieved_gain.realized_pnl == Decimal("998.00")
    assert retrieved_gain.sell_trade.buy_sell == "SELL"
    assert retrieved_gain.buy_lot.symbol == "AAPL"
