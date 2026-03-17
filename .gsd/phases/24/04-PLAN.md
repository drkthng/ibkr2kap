---
phase: 24
plan: 4
wave: 4
---

# Phase 24, Plan 4: E2E Verification & UI Scaffolding

Perform E2E verification with the 2023 XML file and prepare UI flags for Steuerberater review.

## Tasks

### 1. Run E2E Test with 2023 XML
Verify that LMN spinoff lots are created and matched correctly.
- **File**: `tests/test_e2e_corporate_actions.py`

### 2. Update Tax Report Scaffolding
Ensure `PENDING_REVIEW` flag is carried through to the aggregation layer.
- **File**: `src/ibkr_tax/services/tax_aggregator.py`

## Verification
- `uv run pytest tests/test_e2e_corporate_actions.py`
- Manual verification of generated report flags.
