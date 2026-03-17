import pytest
from decimal import Decimal
from ibkr_tax.services.flex_parser import FlexXMLParser
from ibkr_tax.db.repository import import_accounts, import_trades, import_corporate_actions
from ibkr_tax.services.fifo_runner import FIFORunner
from ibkr_tax.models.database import Account, FIFOLot, Gain, CorporateAction

def test_e2e_lmn_spinoff_flow(db_session):
    # This test uses the real 2023 XML provided by the user
    path = "example/U7230673_IBKR2KAP_Full_Export_2023.xml"
    parser = FlexXMLParser(xml_path=path)
    
    # 1. Import Account
    acc_schemas = parser.get_accounts()
    import_accounts(db_session, acc_schemas)
    
    # Get internal account ID for the runner
    acc_id = db_session.query(Account).filter_by(account_id="U7230673").first().id
    
    # 2. Import Corporate Actions (Raw XML parsing)
    ca_schemas = parser.get_corporate_actions()
    import_corporate_actions(db_session, ca_schemas)
    
    # 3. Import Trades
    trade_schemas = parser.get_trades()
    import_trades(db_session, trade_schemas)
    
    db_session.commit()
    
    # 4. Run FIFO
    runner = FIFORunner(db_session)
    runner.run_for_account(acc_id)
    
    # 5. Verify LMN Spinoff and Fractional Sell
    # Expected: 3.0004 shares via SO, -0.0004 shares via Sell -> 3.0 shares remaining
    lmn_lots = db_session.query(FIFOLot).filter_by(symbol="LMN").all()
    assert len(lmn_lots) == 1
    lot = lmn_lots[0]
    assert lot.original_quantity == Decimal("3.0004")
    assert lot.remaining_quantity == Decimal("3.0000") # Exactly 3.0 after fractional sell
    
    # Verify Gain for LMN
    lmn_gains = db_session.query(Gain).join(FIFOLot).filter(FIFOLot.symbol == "LMN").all()
    assert len(lmn_gains) == 1
    gain = lmn_gains[0]
    assert gain.quantity_matched == Decimal("0.0004")
    assert gain.realized_pnl == Decimal("0") # IBKR usually shows 0 for fractional spinoff sell
    
    # Verify Corporate Action record
    lmn_ca = db_session.query(CorporateAction).filter_by(symbol="LMN", action_type="SO").first()
    assert lmn_ca is not None
    assert lmn_ca.tax_treatment == "PENDING_REVIEW"
    assert lot.corporate_action_id == lmn_ca.id
