# Phase 7 Verification: FIFO Engine

## Goal
The absolute core of the app: chronological matching of BUY and SELL lots matching the strict German FIFO laws across tax years.

## Must-Haves Verification
- [x] Chronological matching (FIFO) based on settlement date — **VERIFIED**
    - Logic implemented in `fifo.py` using `asc(FIFOLot.settle_date)`.
    - Tested in `tests/test_fifo.py::test_multiple_buys_one_sell`.
- [x] Precise EUR PnL calculation — **VERIFIED**
    - Logic uses `Decimal` and `fx_rate_to_base`.
    - Tested in `tests/test_fifo.py::test_basic_fifo_matching` with non-1.0 FX rates.
- [x] Handle fractional quantities — **VERIFIED**
    - Tested in `tests/test_fifo.py::test_fractional_shares`.
- [x] Idempotent runner — **VERIFIED**
    - `FIFORunner` clears existing data for the account before processing.
    - Tested in `tests/test_fifo_runner.py::test_runner_idempotency`.

## Verdict: PASS
Phase 7 is fully implemented and verified against the specification.
