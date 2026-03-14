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
    fifo_lots: Mapped[List["FIFOLot"]] = relationship(back_populates="trade")
    gains: Mapped[List["Gain"]] = relationship(back_populates="sell_trade")

class FIFOLot(Base):
    """FIFOLot model tracking open units for FIFO matching."""
    __tablename__ = "fifo_lots"

    id: Mapped[int] = mapped_column(primary_key=True)
    trade_id: Mapped[int] = mapped_column(ForeignKey("trades.id"))
    asset_category: Mapped[str] = mapped_column()
    symbol: Mapped[str] = mapped_column(index=True)
    settle_date: Mapped[str] = mapped_column(index=True)
    original_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    remaining_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    cost_basis_total: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    cost_basis_per_share: Mapped[Decimal] = mapped_column(Numeric(18, 4))

    trade: Mapped["Trade"] = relationship(back_populates="fifo_lots")
    gains: Mapped[List["Gain"]] = relationship(back_populates="buy_lot")

class Gain(Base):
    """Gain model tracking realized PnL and tax pools."""
    __tablename__ = "gains"

    id: Mapped[int] = mapped_column(primary_key=True)
    sell_trade_id: Mapped[int] = mapped_column(ForeignKey("trades.id"))
    buy_lot_id: Mapped[int] = mapped_column(ForeignKey("fifo_lots.id"))
    quantity_matched: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    tax_year: Mapped[int] = mapped_column(index=True)
    proceeds: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    cost_basis_matched: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    realized_pnl: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    tax_pool: Mapped[str] = mapped_column()  # Enum: Aktien, Termingeschäfte, Sonstige

    sell_trade: Mapped["Trade"] = relationship(back_populates="gains")
    buy_lot: Mapped["FIFOLot"] = relationship(back_populates="gains")

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
