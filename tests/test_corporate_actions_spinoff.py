import pytest
from decimal import Decimal
from datetime import date
from ibkr_tax.models.database import Account, Trade, FIFOLot, CorporateAction
from ibkr_tax.services.corporate_actions import CorporateActionEngine
from ibkr_tax.schemas.ibkr import CorporateActionSchema
from ibkr_tax.services.fifo import FIFOEngine

@pytest.fixture
def account(db_session):
    acc = Account(account_id="U7230673", currency="CAD")
    db_session.add(acc)
    db_session.flush()
    return acc

def test_spinoff_creates_virtual_fifo_lot(db_session, account):
    # Setup: Create CorporateAction record first (as required by apply_spinoff for ca_id)
    ca = CorporateAction(
        account_id=account.id,
        symbol="LMN",
        parent_symbol="CSU",
        action_type="SO",
        date="2023-02-14",
        report_date="2023-02-15",
        quantity=Decimal("3.0004"),
        currency="CAD",
        transaction_id="1673457852",
        description="CSU SPINOFF"
    )
    db_session.add(ca)
    db_session.flush()

    action = CorporateActionSchema(
        account_id="U7230673",
        symbol="LMN",
        parent_symbol="CSU",
        action_type="SO",
        date=date(2023, 2, 14),
        report_date=date(2023, 2, 15),
        quantity=Decimal("3.0004"),
        value=Decimal("0"),
        currency="CAD",
        transaction_id="1673457852",
        description="CSU SPINOFF"
    )

    ca_engine = CorporateActionEngine(db_session)
    ca_engine.apply(action)

    # Verification
    stmt = db_session.query(FIFOLot).filter_by(symbol="LMN").first()
    assert stmt is not None
    assert stmt.original_quantity == Decimal("3.0004")
    assert stmt.trade_id is None
    assert stmt.corporate_action_id == ca.id
    assert stmt.settle_date == "2023-02-14"

def test_spinoff_lot_matchable_by_sell(db_session, account):
    # 1. Apply Spinoff
    ca = CorporateAction(
        account_id=account.id, symbol="LMN", action_type="SO",
        date="2023-02-14", report_date="2023-02-15",
        quantity=Decimal("3.0004"), currency="CAD",
        transaction_id="1673457852", description="CSU SPINOFF"
    )
    db_session.add(ca)
    db_session.flush()
    
    action = CorporateActionSchema(
        account_id="U7230673", symbol="LMN", action_type="SO",
        date=date(2023, 2, 14), report_date=date(2023, 2, 15),
        quantity=Decimal("3.0004"), currency="CAD",
        transaction_id="1673457852", description="CSU SPINOFF"
    )
    CorporateActionEngine(db_session).apply(action)

    # 2. Process a SELL trade for the fractional part
    sell_trade = Trade(
        account_id=account.id, ib_trade_id="T1", asset_category="STK",
        symbol="LMN", description="Fractional Sell",
        trade_date="2023-02-15", settle_date="2023-02-15",
        quantity=Decimal("-0.0004"), trade_price=Decimal("0"),
        currency="CAD", fx_rate_to_base=Decimal("1"),
        proceeds=Decimal("0"), ib_commission=Decimal("0"), taxes=Decimal("0"),
        buy_sell="SELL"
    )
    db_session.add(sell_trade)
    db_session.flush()

    fifo_engine = FIFOEngine(db_session)
    fifo_engine.process_trade(sell_trade)

    # 3. Verify matching
    lot = db_session.query(FIFOLot).filter_by(symbol="LMN").first()
    assert lot.remaining_quantity == Decimal("3.0000")
    
    from ibkr_tax.models.database import Gain
    gain = db_session.query(Gain).first()
    assert gain is not None
    assert gain.quantity_matched == Decimal("0.0004")
