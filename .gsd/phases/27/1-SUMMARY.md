---
phase: 27
plan: 1
---

# Plan 27.1 Summary: Transfer Schema, Parser & Database Model

## What Was Done
- Added `TransferSchema` to `ibkr.py` with all fields from IBKR XML
- Created `Transfer` DB model with UniqueConstraint for dedup
- Added `transfer_id` FK to `FIFOLot` for traceability
- Implemented `get_transfers()` in `flex_parser.py` using raw ElementTree
- Added `import_transfers()` to `repository.py`
- Integrated into `pipeline.py` (import + counts)
- Added `Transfers` to `ignored_tags` (no longer unmapped entity)

## Verification
- 86/86 tests pass, 0 regressions
