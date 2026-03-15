import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from ibkr_tax.models.database import Base

@pytest.fixture
def db_engine():
    """Provides a session-wide SQLite in-memory engine."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine

@pytest.fixture
def db_session(db_engine):
    """Provides a transactional database session."""
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.rollback()
    session.close()
