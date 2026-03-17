from decimal import Decimal
from sqlalchemy import Numeric, ForeignKey, UniqueConstraint
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
    corporate_actions: Mapped[List["CorporateAction"]] = relationship(back_populates="account")
    fx_fifo_lots: Mapped[List["FXFIFOLot"]] = relationship(back_populates="account")
    fx_gains: Mapped[List["FXGain"]] = relationship(back_populates="account")

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
    open_close_indicator: Mapped[str] = mapped_column(nullable=True)

    account: Mapped["Account"] = relationship(back_populates="trades")
    fifo_lots: Mapped[List["FIFOLot"]] = relationship(back_populates="trade")
    gains: Mapped[List["Gain"]] = relationship(back_populates="sell_trade")

class CorporateAction(Base):
    """CorporateAction model tracking events like stock splits and spinoffs."""
    __tablename__ = "corporate_actions"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    symbol: Mapped[str] = mapped_column(index=True)
    parent_symbol: Mapped[str | None] = mapped_column(nullable=True)
    action_type: Mapped[str] = mapped_column()  # SO, RS, RI, DW, DI, ED
    date: Mapped[str] = mapped_column(index=True)   # ISO date YYYY-MM-DD
    report_date: Mapped[str] = mapped_column()      # ISO date YYYY-MM-DD
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    value: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0)
    isin: Mapped[str | None] = mapped_column(nullable=True)
    currency: Mapped[str] = mapped_column()
    transaction_id: Mapped[str] = mapped_column(unique=True, index=True)
    description: Mapped[str] = mapped_column()
    tax_treatment: Mapped[str] = mapped_column(default="PENDING_REVIEW")

    account: Mapped["Account"] = relationship(back_populates="corporate_actions")
    fifo_lots: Mapped[List["FIFOLot"]] = relationship(back_populates="corporate_action")

class FIFOLot(Base):
    """FIFOLot model tracking open units for FIFO matching."""
    __tablename__ = "fifo_lots"

    id: Mapped[int] = mapped_column(primary_key=True)
    trade_id: Mapped[int | None] = mapped_column(ForeignKey("trades.id"), nullable=True)
    corporate_action_id: Mapped[int | None] = mapped_column(ForeignKey("corporate_actions.id"), nullable=True)
    asset_category: Mapped[str] = mapped_column()
    symbol: Mapped[str] = mapped_column(index=True)
    settle_date: Mapped[str] = mapped_column(index=True)
    original_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    remaining_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    cost_basis_total: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    cost_basis_per_share: Mapped[Decimal] = mapped_column(Numeric(18, 4))

    trade: Mapped["Trade"] = relationship(back_populates="fifo_lots")
    corporate_action: Mapped["CorporateAction"] = relationship(back_populates="fifo_lots")
    gains: Mapped[List["Gain"]] = relationship(back_populates="buy_lot")

class Gain(Base):
    """Gain model tracking realized PnL and tax pools."""
    __tablename__ = "gains"

    id: Mapped[int] = mapped_column(primary_key=True)
    sell_trade_id: Mapped[int | None] = mapped_column(ForeignKey("trades.id"), nullable=True)
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

class FXFIFOLot(Base):
    """FXFIFOLot model tracking open units of foreign currency for FIFO matching."""
    __tablename__ = "fx_fifo_lots"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    currency: Mapped[str] = mapped_column(index=True)
    acquisition_date: Mapped[str] = mapped_column(index=True)
    original_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    remaining_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    cost_basis_total_eur: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    cost_basis_per_unit_eur: Mapped[Decimal] = mapped_column(Numeric(18, 6))

    # Optional tracing
    trade_id: Mapped[int | None] = mapped_column(ForeignKey("trades.id"), nullable=True)
    cash_transaction_id: Mapped[int | None] = mapped_column(ForeignKey("cash_transactions.id"), nullable=True)

    account: Mapped["Account"] = relationship(back_populates="fx_fifo_lots")

class FXGain(Base):
    """FXGain model tracking realized FX PnL under § 23 EStG."""
    __tablename__ = "fx_gains"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    fx_lot_id: Mapped[int] = mapped_column(ForeignKey("fx_fifo_lots.id"))
    disposal_date: Mapped[str] = mapped_column(index=True)
    amount_matched: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    disposal_proceeds_eur: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    cost_basis_matched_eur: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    realized_pnl_eur: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    days_held: Mapped[int] = mapped_column()
    is_taxable_section_23: Mapped[bool] = mapped_column(default=False)

    account: Mapped["Account"] = relationship(back_populates="fx_gains")
    fx_lot: Mapped["FXFIFOLot"] = relationship()

class ExchangeRate(Base):
    """ExchangeRate model caching ECB reference rates."""
    __tablename__ = "exchange_rates"
    __table_args__ = (
        UniqueConstraint("rate_date", "source_currency", name="uq_rate_date_currency"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    rate_date: Mapped[str] = mapped_column(index=True)  # ISO date string YYYY-MM-DD
    source_currency: Mapped[str] = mapped_column()       # e.g. "USD", "GBP"
    rate_to_eur: Mapped[Decimal] = mapped_column(Numeric(18, 6))
