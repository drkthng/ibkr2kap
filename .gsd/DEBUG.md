# Debug Session: Missing Cost Basis Filtering

## Symptom
When generating a tax report for a specific tax year (e.g., 2021), the missing cost basis warnings include trades that occurred in subsequent years (e.g., 2022).
**When:** Generating the tax report.
**Expected:** The report should only warn about missing cost basis for trades that are relevant to the requested tax year (e.g., sell trades that occurred in the report year or affect the report year).
**Actual:** Missing cost basis warnings from all years are returned, including those in the future compared to the report year.

## Hypotheses

| # | Hypothesis | Likelihood | Status |
|---|------------|------------|--------|
| 1 | `TaxAggregatorService.generate_report` does not filter `stmt_missing` by `tax_year`. | 95% | UNTESTED |

## Attempts

## Resolution

**Root Cause:** The `FIFOLot` query for missing cost basis was unbounded by the tax year, causing it to return sell-trades from future years.
**Fix:** Added a `settle_date` filter to the query in `TaxAggregatorService.generate_report`.
**Verified:** Added a multi-year test case to `tests/test_tax_aggregator.py` and ran the full test suite.
**Regression Check:** All 17 tests passed.

