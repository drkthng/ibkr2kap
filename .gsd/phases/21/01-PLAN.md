---
phase: 21
plan: 1
wave: 1
---

# Plan: Fix Missing Cost Basis Filtering

## Goal
Restrict missing cost basis warnings to the specific tax year requesting the report.

## Tasks

### Task 1: Update Tax Aggregator
Update the `FIFOLot` query in `TaxAggregatorService` to filter by the `tax_year`.
<task>
Modify `src/ibkr_tax/services/tax_aggregator.py` to add the `settle_date` filter.
</task>
<verify>
Check if `Trade.settle_date.like(f"{tax_year}%")` is added to the `stmt_missing` query.
</verify>

### Task 2: Update Unit Tests
Add a multi-year scenario to the aggregator tests to ensure filtering works as expected.
<task>
Modify `tests/test_tax_aggregator.py`.
</task>
<verify>
Run `.venv\Scripts\python.exe -m pytest tests/test_tax_aggregator.py`
</verify>

### Task 3: Regression Testing
Ensure no breakages in other parts of the system.
<task>
Run all tests.
</task>
<verify>
Run `.venv\Scripts\python.exe -m pytest tests`
</verify>
