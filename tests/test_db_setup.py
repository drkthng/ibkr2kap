from decimal import Decimal
from ibkr_tax.db.engine import get_engine, init_db
from ibkr_tax.models.database import Base, Account, Trade, CashTransaction, FIFOLot, Gain

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
        ib_trade_id="TR-BUY-1",
        account_id=account.id,
        asset_category="STK",
        symbol="AAPL",
        description="APPLE INC",
        trade_date="2023-01-01",
        settle_date="2023-01-03",
        currency="USD",
        fx_rate_to_base=Decimal("0.93"),
        quantity=Decimal("100"),
        trade_price=Decimal("150.00"),
        proceeds=Decimal("-15000.00"),
        ib_commission=Decimal("1.00"),
        buy_sell="BUY",
        open_close_indicator="O"
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
        cost_basis_total=Decimal("13951.00"),  # (15000 * 0.93) + commission? simplified
        cost_basis_per_share=Decimal("139.51")
    )
    db_session.add(lot)
    db_session.flush()

    # 4. Create Trade (SELL)
    trade_sell = Trade(
        ib_trade_id="TR-SELL-1",
        account_id=account.id,
        asset_category="STK",
        symbol="AAPL",
        description="APPLE INC",
        trade_date="2023-02-01",
        settle_date="2023-02-03",
        currency="USD",
        fx_rate_to_base=Decimal("0.94"),
        quantity=Decimal("-100"),
        trade_price=Decimal("160.00"),
        proceeds=Decimal("16000.00"),
        ib_commission=Decimal("1.00"),
        buy_sell="SELL",
        open_close_indicator="C"
    )
    db_session.add(trade_sell)
    db_session.flush()

    # 5. Create Gain
    gain = Gain(
        sell_trade_id=trade_sell.id,
        buy_lot_id=lot.id,
        quantity_matched=Decimal("100"),
        tax_year=2023,
        proceeds=Decimal("15040.00"),
        cost_basis_matched=Decimal("13951.00"),
        realized_pnl=Decimal("1089.00"),
        tax_pool="Aktien"
    )
    db_session.add(gain)

    # 6. Create CashTransaction
    cash_tx = CashTransaction(
        account_id=account.id,
        symbol="AAPL",
        description="AAPL(US0378331005) CASH DIVIDEND",
        date_time="2023-05-01;202000",
        settle_date="2023-05-01",
        amount=Decimal("24.00"),
        type="Dividends",
        currency="USD",
        fx_rate_to_base=Decimal("0.92"),
        action_id="DIV-123",
        report_date="2023-05-01"
    )
    db_session.add(cash_tx)
    
    db_session.commit()

    # Verification
    retrieved_acc = db_session.query(Account).filter_by(account_id="U1234567").first()
    assert retrieved_acc is not None
    assert len(retrieved_acc.trades) == 2
    assert len(retrieved_acc.cash_transactions) == 1

    retrieved_lot = db_session.query(FIFOLot).filter_by(symbol="AAPL").first()
    assert retrieved_lot.remaining_quantity == Decimal("100")
    assert retrieved_lot.trade.trade_date == "2023-01-01"

    retrieved_gain = db_session.query(Gain).first()
    assert retrieved_gain.realized_pnl == Decimal("1089.00")
    assert retrieved_gain.sell_trade.buy_sell == "SELL"
    assert retrieved_gain.buy_lot.symbol == "AAPL"
