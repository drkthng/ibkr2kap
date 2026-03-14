from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    """Base class for all models."""
    pass

class Account(Base):
    """Dummy Account model for testing scaffolding."""
    __tablename__ = "accounts"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[str] = mapped_column(unique=True, index=True)
