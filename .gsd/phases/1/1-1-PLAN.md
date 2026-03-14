---
phase: 1
plan: 1
wave: 1
---

# Plan 1.1: Core Database Models (Account, Trade, Dividend)

## Objective
Establish the primary base classes and core transactional models (Accounts, Trades, Dividends) using strictly typing and SQLAlchemy 2.0 ORM features. This ensures basic data structures exist before complex tax-tracking models. 

## Context
- .gsd/SPEC.md
- .gsd/ROADMAP.md
- src/ibkr_tax/models/database.py

## Tasks

<task type="auto">
  <name>Refine Base and Common Types</name>
  <files>src/ibkr_tax/models/database.py</files>
  <action>
    - Ensure `Base` class is set up correctly in `database.py`.
    - Setup strict usage of `decimal.Decimal` or `Numeric` for all monetary amounts by utilizing `Mapped[Decimal]`.
    - DO NOT use typical `float` or standard `int` mappings for financial metrics. Set precision appropriately (e.g. `Numeric(18, 4)` for currency matching IBKR constraints).
  </action>
  <verify>pytest -v tests/test_db_setup.py</verify>
  <done>Base class and Numeric type annotations exist without float definitions.</done>
</task>

<task type="auto">
  <name>Implement Account and Trade Models</name>
  <files>src/ibkr_tax/models/database.py</files>
  <action>
    - Expand the existing `Account` dummy model. Fields required: `id`, `account_id`, `currency`. 
    - Create a `Trade` model.
    - `Trade` fields should include: `id`, `account_id` (foreign key), `asset_category` (e.g. STK, OPT, CASH), `symbol`, `trade_date` (Date), `settle_date` (Date), `quantity` (Numeric), `trade_price` (Numeric), `taxes` (Numeric), `ib_commission` (Numeric), `buy_sell` (String).
    - Ensure proper relationships between `Account` and its `Trades`.
  </action>
  <verify>python -c "from ibkr_tax.models.database import Account, Trade"</verify>
  <done>Account and Trade models successfully import and map cleanly without SQLAlchemy relationship errors.</done>
</task>

<task type="auto">
  <name>Implement Dividend Model</name>
  <files>src/ibkr_tax/models/database.py</files>
  <action>
    - Create a `Dividend` model matching IBKR specifications.
    - Fields should include: `id`, `account_id` (foreign key), `symbol`, `pay_date` (Date), `gross_rate` (Numeric), `gross_amount` (Numeric), `withholding_tax` (Numeric), `currency` (String).
  </action>
  <verify>python -c "from ibkr_tax.models.database import Dividend"</verify>
  <done>Dividend model exists and maps cleanly in the schema.</done>
</task>

## Success Criteria
- [ ] Strict types without `float` usage enforced for Trade and Dividend models.
- [ ] Account, Trade, and Dividend mapped to SQLite tables perfectly.
- [ ] Tests confirm ORM relationships.
