---
phase: 27
plan: 2
---

# Plan 27.2 Summary: FIFO Lot Migration Engine & Tests

## What Was Done
- Created `transfer_engine.py` with `TransferEngine` class
  - `process_transfers()` — batch processes all IN-direction stock transfers
  - `_process_single_transfer()` — processes individual transfer (used by FIFORunner)
- Updated `fifo_runner.py`:
  - Interleaves transfers with trades/corporate actions by settle_date
  - Transfer events processed before corporate actions and trades on same date
  - `_clear_fifo_data()` now clears transfer-sourced FIFOLots
- Created `test_transfer_engine.py` with 11 tests:
  - Stock IN creates FIFOLot with correct cost basis from positionAmountInBase
  - Stock OUT creates no FIFOLot
  - Cash-only (qty=0, symbol="--") creates no FIFOLot
  - Idempotent processing (double-run creates lots once)
  - Transferred lot participates in FIFO sell matching
  - Parser tests: stock transfer, cash transfer, parse_all, unmapped entities

## Verification
- 97/97 tests pass (86 existing + 11 new), 0 regressions
