from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.schema import MetaData

def get_engine(db_url: str = "sqlite:///ibkr_tax.db"):
    """Returns a SQLAlchemy engine."""
    return create_engine(db_url, echo=False)

def get_session(engine) -> sessionmaker:
    """Returns a configured Session class."""
    return sessionmaker(bind=engine)

def init_db(engine, base_metadata: MetaData):
    """Creates all tables defined in the metadata."""
    base_metadata.create_all(engine)
