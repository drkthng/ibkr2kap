---
phase: 35
plan: 3
wave: 3
---

# Plan 35.3: Streamlit UI — Multi-Account Selection & Combined Report

## Objective
Update the Streamlit UI (Tab 4: Anlage KAP Report) to allow users to select multiple
accounts and generate either a single-account or combined report. Add the combined 
Excel export button alongside the existing single-account flow.

## Context
- .gsd/SPEC.md
- src/app.py (Tab 4 section, lines ~311-471)
- src/ibkr_tax/services/tax_aggregator.py (generate_combined_report)
- src/ibkr_tax/services/excel_export.py (export_combined)

## Tasks

<task type="auto">
  <name>Update Tab 4 UI for multi-account selection</name>
  <files>src/app.py</files>
  <action>
    In Tab 4 ("Anlage KAP Report"), replace the single-account `st.selectbox` with
    `st.multiselect` for account selection:
    
    1. Replace `st.selectbox("IBKR Account ID", ...)` with 
       `st.multiselect("IBKR Account(s)", options=available_accounts, default=available_accounts)`
    2. When only 1 account is selected → use existing single-account flow (TaxAggregatorService.generate_report + ExcelExportService.export)
    3. When 2+ accounts selected → use new combined flow:
       a. Call `aggregator.generate_combined_report(selected_accounts, tax_year)`
       b. Display combined metrics at the top with header "Combined Report (X Accounts)"
       c. Below combined metrics, add an expander per account showing individual metrics
       d. For warnings: merge and display all missing_cost_basis_warnings
       e. Excel export: call `exporter.export_combined(combined_report, path)` with
          filename `Anlage_KAP_Combined_{tax_year}.xlsx`
    
    4. Get available tax years by calling get_tax_years_for_account for EACH selected
       account and taking the intersection (years all accounts have data for).
    
    Important: Keep backward compatibility. If user selects one account, the behavior
    should be identical to the current single-account flow.
  </action>
  <verify>Manual verification: run `python -m streamlit run src/app.py --server.port 8503` and test in browser</verify>
  <done>UI shows multiselect, combined report generates when 2+ accounts selected, single-account still works</done>
</task>

<task type="checkpoint:human-verify">
  <name>Visual verification of combined report UI</name>
  <files>src/app.py</files>
  <action>
    User: Please verify the following in the browser:
    1. Tab 4 shows a multi-select dropdown for accounts
    2. Selecting one account shows the report as before
    3. Selecting two accounts shows "Combined Report (2 Accounts)" with summed metrics
    4. Individual account breakdowns appear in expanders below
    5. Excel export creates a file with combined summary and account columns in detail tabs
  </action>
  <verify>User confirms visual behavior</verify>
  <done>User approves combined report UI behavior</done>
</task>

## Success Criteria
- [ ] Multi-account selection available via st.multiselect
- [ ] Combined metrics display correctly when 2+ accounts selected
- [ ] Single-account flow unchanged
- [ ] Combined Excel export works from UI
- [ ] User verifies behavior in browser
