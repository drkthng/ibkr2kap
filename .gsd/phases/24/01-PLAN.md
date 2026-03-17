---
phase: 24
plan: 1
wave: 1
---

# Phase 24, Plan 1: Schema & DB Model Refactor

Refactor the corporate action schema and database model to support advanced types (SO, RI, DW, DI, ED, RS) and traceability.

## Tasks

### 1. Update `ibkr.py` Schema
Expand `CorporateActionSchema` with new fields and types.
- **File**: `src/ibkr_tax/schemas/ibkr.py`
- **Verify**: `pytest tests/test_schemas.py`

### 2. Update `database.py` Models
Modify `CorporateAction` and `FIFOLot` models for advance action tracking and nullability.
- **File**: `src/ibkr_tax/models/database.py`
- **Verify**: `pytest tests/test_db_setup.py`

### 3. Update Repository Imports
Adjust `import_corporate_actions` to use `transaction_id`.
- **File**: `src/ibkr_tax/db/repository.py`
- **Verify**: `pytest tests/test_repository.py`

## Verification
- `uv run pytest tests/test_schemas.py tests/test_db_setup.py tests/test_repository.py`
