---
phase: 17
plan: 1
wave: 1
---

# Plan 17.1: Repository Queries for Dynamic Dropdowns

## Objective
Add two new repository functions to query the database for distinct account IDs and distinct tax years per account. These provide the data layer for the dynamic UI dropdowns.

## Context
- .gsd/SPEC.md
- src/ibkr_tax/db/repository.py
- src/ibkr_tax/models/database.py
- tests/test_repository.py

## Tasks

<task type="auto">
  <name>Add get_distinct_account_ids() to repository</name>
  <files>src/ibkr_tax/db/repository.py</files>
  <action>
    Add a function `get_distinct_account_ids(session: Session) -> list[str]` that:
    - Queries `Account.account_id` from the `accounts` table
    - Returns a sorted list of distinct string account IDs (e.g. ["U1234567", "U9876543"])
    - Returns empty list if no accounts exist
    - Do NOT use raw SQL; use SQLAlchemy ORM select()
  </action>
  <verify>pytest tests/test_repository.py -v -k "test_get_distinct_account_ids"</verify>
  <done>Function returns sorted list of string account IDs. Empty list when no accounts exist.</done>
</task>

<task type="auto">
  <name>Add get_tax_years_for_account() to repository</name>
  <files>src/ibkr_tax/db/repository.py</files>
  <action>
    Add a function `get_tax_years_for_account(session: Session, account_identifier: str) -> list[int]` that:
    - Resolves the string account_identifier to the internal Account.id
    - Queries DISTINCT `Gain.tax_year` for gains linked to trades of that account (join Gain -> Trade on sell_trade_id, filter Trade.account_id == internal_id)
    - Also collects distinct years from `CashTransaction.settle_date` (extract year via substr) for the same account
    - Merges both sets and returns a sorted list of unique integer years (descending: newest first)
    - Returns empty list if account not found or no data exists
    - Do NOT use raw SQL; use SQLAlchemy ORM
    - WHY both sources: Tax year may have only dividends (CashTransaction) or only gains (Gain table). The dropdown should show any year with activity.
  </action>
  <verify>pytest tests/test_repository.py -v -k "test_get_tax_years_for_account"</verify>
  <done>Function returns sorted (desc) list of integer tax years. Merges gain years and cash transaction years. Empty list when no data.</done>
</task>

<task type="auto">
  <name>Write unit tests for both repository functions</name>
  <files>tests/test_repository.py</files>
  <action>
    Add the following tests to the EXISTING test file `tests/test_repository.py`:

    1. `test_get_distinct_account_ids_empty` — No accounts → returns []
    2. `test_get_distinct_account_ids_multiple` — Two accounts inserted → returns sorted list of both
    3. `test_get_tax_years_for_account_empty` — Valid account, no gains/cash → returns []
    4. `test_get_tax_years_for_account_with_gains` — Account with gains in 2023 and 2024 → returns [2024, 2023]
    5. `test_get_tax_years_for_account_with_cash_only` — Account with only cash transactions in 2024 → returns [2024]
    6. `test_get_tax_years_for_account_merged` — Account with gains in 2023 and cash in 2024 → returns [2024, 2023]
    7. `test_get_tax_years_for_account_unknown` — Unknown account ID → returns []

    Use the existing `session` fixture pattern from test_repository.py for consistency.
  </action>
  <verify>pytest tests/test_repository.py -v</verify>
  <done>All 7 new tests pass. Existing tests still pass.</done>
</task>

## Success Criteria
- [ ] `get_distinct_account_ids()` returns sorted list of string account IDs
- [ ] `get_tax_years_for_account()` returns sorted (desc) list of integer tax years, merging gain and cash data
- [ ] All 7 new tests pass
- [ ] All existing repository tests still pass
