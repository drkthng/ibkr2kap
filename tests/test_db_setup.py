from ibkr_tax.db.engine import get_engine, init_db
from ibkr_tax.models.database import Base, Account

def test_db_initialization():
    """Tests if the database can be initialized without errors."""
    engine = get_engine("sqlite:///:memory:")
    init_db(engine, Base.metadata)
    assert engine is not None

def test_account_creation(db_session):
    """Tests if the dummy Account model can be saved and retrieved."""
    account = Account(account_id="U1234567")
    db_session.add(account)
    db_session.commit()
    
    retrieved = db_session.query(Account).filter_by(account_id="U1234567").first()
    assert retrieved is not None
    assert retrieved.account_id == "U1234567"
