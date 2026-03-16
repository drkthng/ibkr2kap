---
phase: 17
plan: 2
wave: 2
---

# Plan 17.2: Streamlit UI — Dynamic Dropdowns

## Objective
Replace the static text/number inputs on the "Anlage KAP Report" tab with dynamic `st.selectbox` widgets that are populated from the database. The Tax Year dropdown cascades based on the selected Account ID.

## Context
- .gsd/SPEC.md
- src/app.py (lines 136-189: Tab 3 "Anlage KAP Report")
- src/ibkr_tax/db/repository.py (after Plan 17.1 adds the query functions)

## Tasks

<task type="auto">
  <name>Replace static inputs with dynamic selectboxes in app.py</name>
  <files>src/app.py</files>
  <action>
    Modify the "Anlage KAP Report" tab (Tab 3, currently lines 136-189):

    1. Import the two new repository functions at the top of the file:
       `from ibkr_tax.db.repository import get_distinct_account_ids, get_tax_years_for_account`

    2. Replace the `st.text_input("IBKR Account ID", ...)` with:
       - Call `get_distinct_account_ids(session)` inside a `with SessionLocal() as session:` block
       - Use `st.selectbox("IBKR Account ID", options=account_ids, index=0 if account_ids else None, placeholder="Select an account...")`
       - If no accounts exist, show `st.info("No accounts found. Please import data first.")` and stop

    3. Replace the `st.number_input("Tax Year", ...)` with:
       - Call `get_tax_years_for_account(session, selected_account_id)` to get available years
       - Use `st.selectbox("Tax Year", options=tax_years, index=0 if tax_years else None, placeholder="Select a year...")`
       - If no tax years available, show `st.info("No tax data found for this account. Run FIFO processing or import data with transactions for this account.")`

    4. Keep the rest of the report generation logic unchanged — it already accepts account_id (string) and tax_year (int)

    AVOID:
    - Do NOT wrap the entire tab in a try/except — keep error handling at the individual operation level
    - Do NOT add caching for the dropdowns — Streamlit reruns on selectbox change naturally
    - Do NOT change the report generation or Excel export code at all
  </action>
  <verify>Run `streamlit run src/app.py` locally and verify the dropdowns appear populated on the Anlage KAP Report tab</verify>
  <done>Account ID is a selectbox populated from DB. Tax Year cascades based on selected account. Report generation works unchanged.</done>
</task>

<task type="checkpoint:human-verify">
  <name>Visual verification of dynamic dropdowns</name>
  <files>src/app.py</files>
  <action>
    User visually confirms:
    1. "Anlage KAP Report" tab shows a selectbox for Account ID (not a text input)
    2. Selecting an Account ID updates the Tax Year dropdown to show only relevant years
    3. Generating a report with the selected values still works correctly
    4. When no accounts exist, an info message is shown instead of empty dropdowns
  </action>
  <verify>Manual: Navigate to Anlage KAP Report tab in Streamlit UI</verify>
  <done>User confirms dynamic dropdowns work correctly with cascading behavior</done>
</task>

## Success Criteria
- [ ] Account ID dropdown is populated from the `accounts` table
- [ ] Tax Year dropdown cascades — shows only years with data for the selected account
- [ ] Report generation works with selected dropdown values
- [ ] Graceful message when no accounts or no tax data exists
