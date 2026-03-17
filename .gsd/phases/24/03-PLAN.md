---
phase: 24
plan: 3
wave: 3
---

# Phase 24, Plan 3: Engine & Runner Integration

Implement the spinoff logic in the `CorporateActionEngine` and update the `FIFORunner` to handle the new action types.

## Tasks

### 1. Implement `apply_spinoff`
Create virtual FIFOLots for spinoff shares.
- **File**: `src/ibkr_tax/services/corporate_actions.py`
- **Verify**: New test `tests/test_corporate_actions_spinoff.py`

### 2. Implement Engine Dispatcher
Add `apply()` method to route actions to specific handlers.
- **File**: `src/ibkr_tax/services/corporate_actions.py`

### 3. Update `FIFORunner` Interleaving
Update runner to use the new dispatcher and handle lot deletion.
- **File**: `src/ibkr_tax/services/fifo_runner.py`

## Verification
- `uv run pytest tests/test_corporate_actions_spinoff.py tests/test_fifo_runner.py`
