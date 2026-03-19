---
phase: 36
plan: 1
wave: 1
---

# 01-SCHEMA-PLAN: Schema, Aggregator, and Tooltips

## Goal
Update the core report schema and the aggregator service to handle the new tax-pool-aligned summary fields and remove the old combined P/L field. Update tooltips accordingly.

## Tasks

### T1: Modify Report Schema
**File:** [report.py](file:///d:/Antigravity/IBKR2KAP/src/ibkr_tax/schemas/report.py)
- Remove `total_realized_pnl`
- Add `aktien_net_result`, `allgemeiner_topf_result`, `dividends_interest_total`, `sonstige_gains_total`

### T2: Modify Aggregator Service
**File:** [tax_aggregator.py](file:///d:/Antigravity/IBKR2KAP/src/ibkr_tax/services/tax_aggregator.py)
- Update `generate_report` to compute new fields
- Remove `total_realized_pnl` calculation

### T3: Update Tax Tooltips
**File:** [tax_tooltips.py](file:///d:/Antigravity/IBKR2KAP/src/ibkr_tax/services/tax_tooltips.py)
- Remove `total_realized_pnl`
- Add tooltips for `aktien_net_result`, `allgemeiner_topf_result`

## Verification
- Aggregate unit test: `uv run pytest tests/test_tax_aggregator.py`
- Expect failures initially due to schema changes.
