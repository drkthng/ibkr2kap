---
phase: 35
plan: 2
wave: 2
---

# Plan 35.2: Combined Excel Export

## Objective
Extend `ExcelExportService` with a new `export_combined` method that writes a combined
Excel report: a combined summary at the top, individual account summaries below, and 
an "Account" column added to all detail tabs.

## Context
- .gsd/SPEC.md
- src/ibkr_tax/schemas/report.py (CombinedTaxReport from Plan 35.1)
- src/ibkr_tax/services/excel_export.py
- tests/test_excel_export.py

## Tasks

<task type="auto">
  <name>Add export_combined method to ExcelExportService</name>
  <files>src/ibkr_tax/services/excel_export.py</files>
  <action>
    Add a new public method `export_combined(self, combined_report: CombinedTaxReport, output_path: str)`:
    
    1. **Summary Sheet** ("Anlage KAP Summary"):
       - Title: "IBKR2KAP — Anlage KAP Bericht (Kombiniert)"
       - Accounts line: "Konten: U_ACCT_A, U_ACCT_B"  
       - Combined summary rows (same format as current summary) with summed totals
       - Then a separator row
       - For each per-account report, add a sub-header "Konto: {account_id}" followed 
         by that account's summary rows (same KAP format but indented/offset)
    
    2. **Detail Sheets** (Gains, Dividends, FX, Margin, D&W, Audit Trail):
       - Keep the SAME tab structure (single tab per type, not one per account)
       - Add "Konto" as the FIRST column in each detail sheet
       - For each account in combined_report.per_account_reports, query and append rows
         with the account_id prepended
       - Sort by account_id then by date within each account
    
    3. Reuse existing private methods where possible. For detail sheets, create new
       private methods `_add_combined_*` that loop over accounts internally.
    
    Do NOT modify the existing `export()` method — it remains for single-account use.
  </action>
  <verify>python -m pytest tests/test_excel_export.py -v</verify>
  <done>export_combined method exists and existing tests pass</done>
</task>

<task type="auto">
  <name>Add tests for combined Excel export</name>
  <files>tests/test_excel_export.py</files>
  <action>
    Add test `test_combined_export_creates_correct_sheets`:
    1. Create 2 accounts with trades, gains, and cash transactions
    2. Build a CombinedTaxReport with per_account_reports
    3. Call export_combined() 
    4. Assert all expected sheet names exist
    5. Assert summary sheet has combined totals AND per-account sections
    6. Assert detail sheets have a "Konto" column as first column
    7. Assert detail rows have correct account_id values
  </action>
  <verify>python -m pytest tests/test_excel_export.py::test_combined_export_creates_correct_sheets -v</verify>
  <done>Combined export test passes with correct sheet structure and account columns</done>
</task>

## Success Criteria
- [ ] export_combined produces valid Excel with combined summary
- [ ] Detail sheets have "Konto" as first column
- [ ] All existing single-account export tests still pass
- [ ] New combined test validates structure
