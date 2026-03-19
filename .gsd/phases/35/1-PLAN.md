---
phase: 35
plan: 1
wave: 1
---

# Plan 35.1: Combined Report Schema & Aggregation

## Objective
Extend `TaxReport` schema and `TaxAggregatorService` to support generating a combined 
report that merges multiple accounts into a single aggregate result while preserving
the individual per-account reports.

## Context
- .gsd/SPEC.md
- src/ibkr_tax/schemas/report.py
- src/ibkr_tax/services/tax_aggregator.py
- tests/test_tax_aggregator.py

## Tasks

<task type="auto">
  <name>Add CombinedTaxReport schema</name>
  <files>src/ibkr_tax/schemas/report.py</files>
  <action>
    Create a `CombinedTaxReport` Pydantic model in report.py:
    - Fields: `account_ids: list[str]`, `tax_year: int`
    - All same KAP fields as TaxReport (line 7-15, SO, margin, total)
    - `per_account_reports: list[TaxReport]` — individual account breakdowns
    - `missing_cost_basis_warnings: list[MissingCostBasisWarning]` — merged from all accounts
    
    Keep existing TaxReport unchanged to maintain backward compatibility.
  </action>
  <verify>python -c "from ibkr_tax.schemas.report import CombinedTaxReport; print('OK')"</verify>
  <done>CombinedTaxReport schema importable and instantiable</done>
</task>

<task type="auto">
  <name>Add generate_combined_report method to TaxAggregatorService</name>
  <files>src/ibkr_tax/services/tax_aggregator.py</files>
  <action>
    Add a new method `generate_combined_report(self, account_identifiers: list[str], tax_year: int) -> CombinedTaxReport`:
    1. Call `self.generate_report(account_id, tax_year)` for each account in the list
    2. Sum all KAP fields across the individual reports to get the combined totals
    3. Merge the `missing_cost_basis_warnings` lists
    4. Recalculate `so_fx_freigrenze_applies` based on the combined SO totals
    5. Return a `CombinedTaxReport` with combined totals and the individual reports
    
    Do NOT modify the existing `generate_report` method — it remains untouched.
  </action>
  <verify>python -m pytest tests/test_tax_aggregator.py -v</verify>
  <done>generate_combined_report method exists and all existing tests still pass</done>
</task>

<task type="auto">
  <name>Add unit tests for combined aggregation</name>
  <files>tests/test_tax_aggregator.py</files>
  <action>
    Add a new test `test_generate_combined_report_two_accounts`:
    1. Create two Account objects ("U_ACCT_A" and "U_ACCT_B")
    2. Add Gains (Aktien pool) to each: account A gets +300 gain, account B gets +200 gain
    3. Add CashTransactions (dividends) to each: A gets 100*0.9=90, B gets 50*1.0=50
    4. Call `generate_combined_report(["U_ACCT_A", "U_ACCT_B"], 2024)`
    5. Assert combined kap_line_8 == 500 (300+200)
    6. Assert combined kap_line_7 == 140 (90+50)
    7. Assert len(per_account_reports) == 2
    8. Assert each individual report has correct values
  </action>
  <verify>python -m pytest tests/test_tax_aggregator.py::test_generate_combined_report_two_accounts -v</verify>
  <done>New test passes, confirms combined aggregation sums correctly</done>
</task>

## Success Criteria
- [ ] CombinedTaxReport schema exists and is importable
- [ ] generate_combined_report returns correct combined totals for 2+ accounts
- [ ] All existing tax_aggregator tests still pass
- [ ] New test validates multi-account summing
