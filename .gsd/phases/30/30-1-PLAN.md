---
phase: 30
plan: 1
wave: 1
depends_on: []
files_modified:
  - src/ibkr_tax/schemas/report.py
  - src/ibkr_tax/services/tax_aggregator.py
  - src/app.py
autonomous: true
must_haves:
  truths:
    - Text in warnings must be highly selectable
    - A button next to missing trades pre-fills the manual entry tab
    - Users can upload multiple XML and CSV files at the same time
  artifacts:
    - MissingCostBasisWarning Pydantic schema
---

# Plan 30.1: UX Improvements & Multi-file Import

<objective>
To allow the user to highlight missing trades, prefill manual entries with one click, and batch-upload Flex Query XML/CSV files.
Purpose: Fix friction around manually entering data for positions acquired before the imported timeframe, and speed up importing.
Output: Enhanced `app.py` UI interactions, structured warnings in the backend.
</objective>

<context>
Load for context:
- .gsd/SPEC.md
- src/ibkr_tax/schemas/report.py
- src/ibkr_tax/services/tax_aggregator.py
- src/app.py
</context>

<tasks>

<task type="auto">
  <name>Structure Missing Cost Basis Warnings</name>
  <files>
    - src/ibkr_tax/schemas/report.py
    - src/ibkr_tax/services/tax_aggregator.py
  </files>
  <action>
    - In `schemas/report.py`, create a new Pydantic model `MissingCostBasisWarning` containing `symbol: str`, `quantity: Decimal`, `date: str`, `trade_id: str`, and `message: str`.
    - Change `TaxReport.missing_cost_basis_warnings` type from `list[str]` to `list[MissingCostBasisWarning]`.
    - In `services/tax_aggregator.py`, instead of appending a formatted string to `warnings = []`, build and append a `MissingCostBasisWarning` object using the lot and trade data.
    AVOID: Breaking existing tests by ensuring the message string is preserved exactly as before for backwards compatibility or test expectations.
  </action>
  <verify>pytest</verify>
  <done>TaxReport successfully uses structured warnings and tests pass.</done>
</task>

<task type="auto">
  <name>Enhance Data Import and Warning UI UI</name>
  <files>
    - src/app.py
  </files>
  <action>
    - In `src/app.py`, update `st.file_uploader` for XML and CSV to include `accept_multiple_files=True`. Iterate over the returned file lists rather than processing a single file.
    - Loop over `report.missing_cost_basis_warnings`. For each warning:
      - Display the warning message using normal text/markdown or `st.code(..., language="markdown")` so it is definitely selectable.
      - Add a button "Auto-fill Manual Entry". On click, populate `st.session_state` with `prefill_symbol`, `prefill_qty` (as float), and `prefill_date`, then `st.success` or `st.rerun()`.
    - In the "Manual Positions" tab form, read these `st.session_state.get('prefill_...')` values and inject them into the `value=` argument for `mp_symbol`, `mp_qty`, and `mp_date`.
    AVOID: Writing messy conditional logic for file processing. Use a simple clean `for file in files` loop for the uploaders.
  </action>
  <verify>streamlit run src/app.py builds cleanly</verify>
  <done>Multiple files are uploadable, warnings are displayed correctly with pre-fill buttons, and the form reads the injected default state.</done>
</task>

</tasks>

<verification>
After all tasks, verify:
- [ ] Users can upload multiple XMLs simultaneously.
- [ ] Missing basis warnings render with a button.
- [ ] Clicking the button accurately seeds the manual input fields on the next tab check.
- [ ] Tests pass.
</verification>

<success_criteria>
- [ ] All tasks verified
- [ ] Must-haves confirmed
</success_criteria>
