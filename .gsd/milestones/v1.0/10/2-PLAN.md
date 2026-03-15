---
phase: 10
plan: 2
wave: 1
---

# Plan 10.2: Corporate Actions — Unit Tests

## Objective
Write comprehensive unit tests for the `CorporateActionEngine` to verify stock split behavior across all edge cases: forward splits, reverse splits, multiple lots, partially sold lots, and lots with different symbols (ensuring no cross-contamination).

## Context
- src/ibkr_tax/services/corporate_actions.py
- src/ibkr_tax/schemas/ibkr.py
- tests/conftest.py (db_session fixture)
- tests/test_options.py (pattern for lot-based tests)

## Tasks

<task type="auto">
  <name>Write CorporateAction unit tests</name>
  <files>tests/test_corporate_actions.py</files>
  <action>
    Create `tests/test_corporate_actions.py` with the following tests:

    1. **test_forward_split_4_to_1** — Buy 10 shares at $100 ($1000 total cost). Apply 4:1 split. Verify: qty=40, cost/share=$25, cost_basis_total=$1000 (unchanged).

    2. **test_reverse_split_1_to_10** — Buy 1000 shares at $1 ($1000 total cost). Apply 0.1 ratio (1:10 reverse). Verify: qty=100, cost/share=$10, cost_basis_total=$1000 (unchanged).

    3. **test_split_only_affects_target_symbol** — Buy AAPL (10 shares) and MSFT (20 shares). Apply split to AAPL only. Verify: AAPL lots updated, MSFT lots untouched.

    4. **test_split_only_affects_open_lots** — Buy 10 shares, sell 5 (partially close lot). Apply 4:1 split. Verify: remaining_quantity = 5*4=20, original_quantity = 10*4=40, cost_basis_total unchanged.

    5. **test_split_fully_closed_lot_untouched** — Buy 10 shares, sell all 10. Apply split. Verify: lot with remaining_quantity=0 is NOT modified.

    6. **test_schema_rejects_float** — Ensure CorporateActionSchema raises ValueError when given a float for ratio.

    7. **test_schema_rejects_zero_ratio** — Ensure CorporateActionSchema raises ValueError when ratio is 0.

    Test fixtures: Use existing `db_session` from conftest.py. Create Account + Trade + FIFOLot records per test (following test_options.py pattern).

    AVOID: Using `unittest.mock` — test against real in-memory SQLite.
    AVOID: Overly complex test names — keep them descriptive but concise.
  </action>
  <verify>python -m pytest tests/test_corporate_actions.py -v</verify>
  <done>All 7 tests pass, covering forward/reverse splits, symbol isolation, partial/full lot behavior, and schema validation</done>
</task>

## Success Criteria
- [ ] All 7 tests pass
- [ ] Tests use in-memory SQLite (no mocks)
- [ ] Pattern matches existing test_options.py style
- [ ] No regressions in existing test suite (`python -m pytest`)
