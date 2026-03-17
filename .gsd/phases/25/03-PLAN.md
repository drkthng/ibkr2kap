---
phase: 25
plan: 3
wave: 3
---

# Phase 25, Plan 3: FIFORunner Integration & E2E Verification

## Objective
Update the FIFORunner to pass grouped split events to the engine, and verify end-to-end with the real 2023 XML that DEC's 40,000 old shares become 2,000 new shares with preserved total cost basis.

## Tasks

### 1. Update FIFORunner to use grouped split events
Modify `run_for_account()` to pre-group RS/FS corporate actions via `group_split_actions()` before interleaving with trades. Grouped events replace the individual RS/FS records in the event timeline.
- **File**: `src/ibkr_tax/services/fifo_runner.py`
- **Verify**: `pytest tests/test_fifo_runner.py` (if exists) or unit test

### 2. E2E test with 2023 XML (DEC reverse split)
Verify the full pipeline processes DEC correctly:
- 40,000 old shares (across multiple buys) → 2,000 new shares after 1-for-20 consolidation
- cost_basis_total preserved for each lot
- Subsequent DEC trade (2023-12-19, 200 shares at new ISIN) creates a normal lot
- **File**: `tests/test_e2e_reverse_split.py`
- **Verify**: `pytest tests/test_e2e_reverse_split.py`

### 3. Full regression test
Ensure no existing tests break.
- **Verify**: `pytest --tb=short -q`

## Success Criteria
- [ ] DEC lots renamed and consolidated in E2E test
- [ ] Total cost basis preserved across all DEC lots
- [ ] 71+ tests passing (no regressions)
