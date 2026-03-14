---
phase: 2
plan: 2
wave: 1
---

# Plan 2.2: Schema Validation Tests

## Objective
Thoroughly test all Pydantic schemas from Plan 2.1 to prove they correctly validate, reject, and coerce IBKR data. Tests ensure that invalid data cannot sneak into the database layer.

## Context
- src/ibkr_tax/schemas/ibkr.py (created in Plan 2.1)
- src/ibkr_tax/models/database.py (Phase 1 models — verify `to_db_dict()` compatibility)
- tests/conftest.py (existing test fixtures)

## Tasks

<task type="auto">
  <name>Write schema validation tests</name>
  <files>tests/test_schemas.py</files>
  <action>
    Create `tests/test_schemas.py` with comprehensive test coverage:

    ### AccountSchema tests
    - Valid creation with defaults
    - Valid creation with explicit currency
    - Reject empty account_id
    - Reject currency > 3 chars

    ### TradeSchema tests
    - Valid BUY trade (positive quantity, correct fields)
    - Valid SELL trade (negative quantity, correct fields)
    - String-to-Decimal coercion works for price/quantity fields
    - Reject float inputs for Decimal fields
    - Reject invalid asset_category
    - Reject invalid buy_sell values
    - Reject settle_date before trade_date
    - Reject zero quantity
    - Reject negative fx_rate_to_base
    - Reject mismatched buy_sell and quantity sign (BUY with negative qty)
    - `to_db_dict()` produces correct output (dates as ISO strings, excludes account_id)

    ### CashTransactionSchema tests
    - Valid dividend transaction
    - Valid withholding tax transaction (negative amount, linked action_id)
    - Optional symbol (None allowed)
    - Optional action_id (None allowed)
    - Reject invalid type
    - Reject empty description
    - String-to-Decimal coercion for amount/fx_rate
    - `to_db_dict()` produces correct output

    Test naming convention: `test_{schema}_{scenario}` (e.g., `test_trade_valid_buy`)
  </action>
  <verify>uv run pytest tests/test_schemas.py -v</verify>
  <done>All tests pass, covering valid creation, rejection of invalid data, coercion, cross-field validation, and to_db_dict output</done>
</task>

<task type="auto">
  <name>Verify schema-to-model round-trip</name>
  <files>tests/test_schemas.py</files>
  <action>
    Add integration tests to `tests/test_schemas.py` that verify the full round-trip:
    1. Create a valid schema instance
    2. Call `to_db_dict()`  
    3. Construct the SQLAlchemy model with the dict (providing required FK fields like integer account_id)
    4. Assert that the model fields match the schema input

    This proves the schemas produce data compatible with Phase 1 models.

    Tests needed:
    - `test_trade_schema_to_model_roundtrip` — TradeSchema → to_db_dict → Trade model
    - `test_cash_tx_schema_to_model_roundtrip` — CashTransactionSchema → to_db_dict → CashTransaction model
  </action>
  <verify>uv run pytest tests/test_schemas.py -v -k "roundtrip"</verify>
  <done>Round-trip tests pass, confirming schema output is compatible with DB models</done>
</task>

## Success Criteria
- [ ] All validation tests pass (valid data accepted, invalid data rejected with clear errors)
- [ ] Decimal coercion from strings verified
- [ ] Float rejection verified
- [ ] Cross-field validation tested (settle_date, buy_sell↔quantity)
- [ ] `to_db_dict()` output verified for all schemas
- [ ] Round-trip schema→model compatibility proven
