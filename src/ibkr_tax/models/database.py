from decimal import Decimal
from sqlalchemy import Numeric, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from typing import List

class Base(DeclarativeBase):
    """Base class for all models."""
    pass

class Account(Base):
    """Account model tracking IBKR accounts."""
    __tablename__ = "accounts"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[str] = mapped_column(unique=True, index=True)
    currency: Mapped[str] = mapped_column(default="EUR")

    trades: Mapped[List["Trade"]] = relationship(back_populates="account")
    dividends: Mapped[List["Dividend"]] = relationship(back_populates="account")

class Trade(Base):
    """Trade model tracking transactional data."""
    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    asset_category: Mapped[str] = mapped_column()
    symbol: Mapped[str] = mapped_column(index=True)
    trade_date: Mapped[str] = mapped_column()  # ISO format string or Date
    settle_date: Mapped[str] = mapped_column(index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    trade_price: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    taxes: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0)
    ib_commission: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0)
    buy_sell: Mapped[str] = mapped_column()

    account: Mapped["Account"] = relationship(back_populates="trades")

class Dividend(Base):
    """Dividend model tracking dividend income."""
    __tablename__ = "dividends"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    symbol: Mapped[str] = mapped_column(index=True)
    pay_date: Mapped[str] = mapped_column(index=True)
    gross_rate: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    gross_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    withholding_tax: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0)
    currency: Mapped[str] = mapped_column()

    account: Mapped["Account"] = relationship(back_populates="dividends")
