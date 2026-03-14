from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator, field_validator


class AccountSchema(BaseModel):
    account_id: str = Field(..., min_length=1)
    currency: str = Field("EUR", max_length=3)

    model_config = ConfigDict(str_strip_whitespace=True)

    def to_db_dict(self) -> dict:
        return self.model_dump()


class BaseIBKRSchema(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        strict=False,  # Allow coercion for strings to Decimal/date
    )

    @field_validator("*", mode="before")
    @classmethod
    def reject_float(cls, v):
        if isinstance(v, float):
            raise ValueError("Floats are not allowed for monetary values. Use strings or Decimals.")
        return v


class TradeSchema(BaseIBKRSchema):
    ib_trade_id: str = Field(..., min_length=1)
    account_id: str = Field(..., min_length=1)  # IBKR Account ID string
    asset_category: Literal["STK", "OPT", "FUT", "CASH", "WAR"]
    symbol: str = Field(..., min_length=1)
    description: str
    trade_date: date
    settle_date: date
    currency: str = Field(..., max_length=3)
    fx_rate_to_base: Decimal = Field(..., gt=0)
    quantity: Decimal = Field(...)
    trade_price: Decimal = Field(..., ge=0)
    proceeds: Decimal
    taxes: Decimal = Field(default=Decimal("0"))
    ib_commission: Decimal = Field(default=Decimal("0"))
    buy_sell: Literal["BUY", "SELL"]
    open_close_indicator: str | None = None

    @model_validator(mode="after")
    def validate_signatures(self) -> "TradeSchema":
        if self.settle_date < self.trade_date:
            raise ValueError("settle_date cannot be before trade_date")

        if self.quantity == 0:
            raise ValueError("quantity cannot be zero")

        if self.buy_sell == "BUY" and self.quantity < 0:
            raise ValueError("BUY trade must have positive quantity")
        if self.buy_sell == "SELL" and self.quantity > 0:
            raise ValueError("SELL trade must have negative quantity")

        return self

    def to_db_dict(self) -> dict:
        data = self.model_dump(exclude={"account_id"})
        # Convert date to ISO string for DB compat as per database.py model
        data["trade_date"] = self.trade_date.isoformat()
        data["settle_date"] = self.settle_date.isoformat()
        return data


class CashTransactionSchema(BaseIBKRSchema):
    account_id: str = Field(..., min_length=1)
    symbol: str | None = None
    description: str
    date_time: str
    settle_date: date
    amount: Decimal
    type: Literal[
        "Dividends",
        "Withholding Tax",
        "Payment In Lieu Of Dividends",
        "Broker Interest Paid",
        "Broker Interest Received",
        "Other Fees",
        "Deposits/Withdrawals",
        "Commission Adjustments",
    ]
    currency: str = Field(..., max_length=3)
    fx_rate_to_base: Decimal = Field(..., gt=0)
    action_id: str | None = None
    report_date: date

    def to_db_dict(self) -> dict:
        data = self.model_dump(exclude={"account_id"})
        # Convert date to ISO string
        data["settle_date"] = self.settle_date.isoformat()
        data["report_date"] = self.report_date.isoformat()
        return data
