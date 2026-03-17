---
phase: 25
plan: 2
wave: 2
---

# Phase 25, Plan 2: Engine Refactor for Reverse Split with Symbol Rename

## Objective
Refactor `CorporateActionEngine.apply_reverse_split()` to handle IBKR's paired RS records: rename FIFOLot symbols from old to new, adjust quantities by ratio, and recalculate cost_basis_per_share. Cost basis total is preserved (tax-neutral under German law).

## Tasks

### 1. Refactor `apply_reverse_split` to accept grouped split data
Rewrite `apply_reverse_split()` to:
- Accept the new symbol, old symbol, and ratio from the grouped split event
- Query FIFOLots by old_symbol (or current symbol for simple splits)
- Rename symbol on all matching FIFOLots to the new symbol
- Multiply remaining_quantity and original_quantity by ratio
- Recalculate cost_basis_per_share = cost_basis_total / original_quantity
- Preserve cost_basis_total (tax-neutral consolidation)
- **File**: `src/ibkr_tax/services/corporate_actions.py`
- **Verify**: New test `tests/test_reverse_split_engine.py`

### 2. Update `apply()` dispatcher for FS type
Route `FS` actions to the same `apply_reverse_split()` handler (forward splits are just ratio > 1).
- **File**: `src/ibkr_tax/services/corporate_actions.py`
- **Verify**: `pytest tests/test_corporate_actions.py`

## Success Criteria
- [ ] FIFOLots with symbol "DEC" renamed to new symbol after reverse split
- [ ] Quantities adjusted by ratio (e.g., 100 shares * 0.05 = 5 shares)
- [ ] cost_basis_total unchanged, cost_basis_per_share recalculated
- [ ] FS dispatched to same handler
