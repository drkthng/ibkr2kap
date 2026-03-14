---
phase: 2
plan: 1
wave: 1
---

# Plan 2.1: Pydantic Validation Schemas

## Objective
Create strict Pydantic v2 validation schemas that validate and normalize raw IBKR Flex Query data before database insertion. These schemas act as the boundary between untrusted external data (XML/CSV parsed fields) and our typed internal domain (SQLAlchemy models from Phase 1).

Each schema must:
- Enforce types (Decimal for money, date/datetime parsing, constrained strings)
- Provide meaningful validation errors for bad input
- Mirror the DB model fields but validate incoming raw data (e.g. string→Decimal coercion)

## Context
- .gsd/SPEC.md
- src/ibkr_tax/models/database.py (Phase 1 models — the target structure)
- .gsd/ROADMAP.md (Phase 2 description)

## Tasks

<task type="auto">
  <name>Create schemas module structure</name>
  <files>src/ibkr_tax/schemas/__init__.py, src/ibkr_tax/schemas/ibkr.py</files>
  <action>
    Create `src/ibkr_tax/schemas/` package with:
    - `__init__.py` — re-exports all schemas
    - `ibkr.py` — all Pydantic schemas

    In `ibkr.py`, define these Pydantic v2 `BaseModel` schemas:

    ### AccountSchema
    - `account_id: str` — must be non-empty, stripped
    - `currency: str` — default "EUR", max 3 chars

    ### TradeSchema
    - `ib_trade_id: str` — non-empty, stripped
    - `account_id: str` — non-empty (external IBKR account ID, NOT the FK int)
    - `asset_category: str` — constrained to known values: "STK", "OPT", "FUT", "CASH", "WAR" 
    - `symbol: str` — non-empty, stripped
    - `description: str` — non-empty
    - `trade_date: date` — parsed from ISO string or date object
    - `settle_date: date` — parsed from ISO string or date object
    - `currency: str` — max 3 chars
    - `fx_rate_to_base: Decimal` — must be > 0
    - `quantity: Decimal` — non-zero
    - `trade_price: Decimal` — must be >= 0
    - `proceeds: Decimal` — any value (negative for buys)
    - `taxes: Decimal` — default 0
    - `ib_commission: Decimal` — default 0
    - `buy_sell: str` — constrained to "BUY" or "SELL"
    - `open_close_indicator: str` — constrained to "O", "C", or "O;C" (or empty)

    Key validations:
    - `settle_date >= trade_date` (settlement cannot be before trade)
    - If `buy_sell == "BUY"`, quantity should be positive; if "SELL", negative
    - Use Pydantic v2 `model_validator` for cross-field checks

    ### CashTransactionSchema
    - `account_id: str` — non-empty
    - `symbol: str | None` — optional (some cash events have no symbol)
    - `description: str` — non-empty
    - `date_time: str` — raw IBKR datetime string (format varies: "YYYY-MM-DD;HHMMSS" or similar)
    - `settle_date: date` — parsed from ISO string or date object
    - `amount: Decimal` — any value
    - `type: str` — constrained to known IBKR cash tx types: "Dividends", "Withholding Tax", "Payment In Lieu Of Dividends", "Broker Interest Paid", "Broker Interest Received", "Other Fees", "Deposits/Withdrawals", "Commission Adjustments"
    - `currency: str` — max 3 chars
    - `fx_rate_to_base: Decimal` — must be > 0
    - `action_id: str | None` — optional, used to link dividends + withholding tax
    - `report_date: date` — parsed from ISO string or date object

    Implementation rules:
    - Use `Annotated[Decimal, ...]` with Pydantic v2 field validators
    - Use `model_config = ConfigDict(strict=False)` to allow string→Decimal coercion
    - Avoid floats entirely: use `BeforeValidator` to convert string inputs to `Decimal` objects
    - Add a `@field_validator` for Decimal fields that rejects float inputs but accepts string/int
  </action>
  <verify>python -c "from ibkr_tax.schemas.ibkr import AccountSchema, TradeSchema, CashTransactionSchema; print('Import OK')"</verify>
  <done>All three schemas importable, Pydantic v2 BaseModel subclasses with typed fields and validators</done>
</task>

<task type="auto">
  <name>Add schema-to-dict helper for DB insertion</name>
  <files>src/ibkr_tax/schemas/ibkr.py</files>
  <action>
    Add a `to_db_dict()` method to each schema that returns a dict ready for SQLAlchemy model construction:
    - Converts `date` fields back to ISO format strings (since DB models store dates as strings)
    - Returns only the fields that map to DB model columns
    - Excludes `account_id` string field from TradeSchema/CashTransactionSchema (since the DB uses integer FK — the caller resolves this)

    This method does NOT create DB objects directly — it just produces a clean dict that can be unpacked into the ORM model constructor.
  </action>
  <verify>python -c "from ibkr_tax.schemas.ibkr import TradeSchema; print('to_db_dict' in dir(TradeSchema))"</verify>
  <done>Each schema has a `to_db_dict()` method that returns a dict suitable for ORM model construction</done>
</task>

## Success Criteria
- [ ] `AccountSchema`, `TradeSchema`, `CashTransactionSchema` defined with strict Pydantic v2 validation
- [ ] Decimal fields reject floats but accept strings and ints
- [ ] Cross-field validators enforce business rules (settle_date >= trade_date, buy_sell↔quantity sign)
- [ ] Each schema has `to_db_dict()` for clean ORM interop
- [ ] All schemas importable from `ibkr_tax.schemas`
