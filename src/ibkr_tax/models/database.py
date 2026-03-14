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
    cash_transactions: Mapped[List["CashTransaction"]] = relationship(back_populates="account")

class Trade(Base):
    """Trade model tracking transactional data."""
    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(primary_key=True)
    ib_trade_id: Mapped[str] = mapped_column(unique=True, index=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    asset_category: Mapped[str] = mapped_column()
    symbol: Mapped[str] = mapped_column(index=True)
    description: Mapped[str] = mapped_column()
    trade_date: Mapped[str] = mapped_column()  # ISO format string or Date
    settle_date: Mapped[str] = mapped_column(index=True)
    currency: Mapped[str] = mapped_column()
    fx_rate_to_base: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    trade_price: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    proceeds: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    taxes: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0)
    ib_commission: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0)
    buy_sell: Mapped[str] = mapped_column()
    open_close_indicator: Mapped[str] = mapped_column()

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

class CashTransaction(Base):
    """CashTransaction model tracking dividends, taxes, interest, etc."""
    __tablename__ = "cash_transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    symbol: Mapped[str] = mapped_column(index=True, nullable=True)
    description: Mapped[str] = mapped_column()
    date_time: Mapped[str] = mapped_column(index=True)
    settle_date: Mapped[str] = mapped_column(index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    type: Mapped[str] = mapped_column()
    currency: Mapped[str] = mapped_column()
    fx_rate_to_base: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    action_id: Mapped[str] = mapped_column(index=True, nullable=True)
    report_date: Mapped[str] = mapped_column()

    account: Mapped["Account"] = relationship(back_populates="cash_transactions")
