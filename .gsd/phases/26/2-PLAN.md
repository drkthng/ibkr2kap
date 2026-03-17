---
phase: 26
plan: 2
wave: 2
---

# Plan 26.2: Integrate Tax Guidance into Streamlit UI

## Objective
Enhance the Streamlit UI with contextual tax guidance so users understand what each number means when viewing their Anlage KAP report. Add a new "📖 Tax Guide" tab and inline help text to the existing report tab.

## Context
- src/app.py (current Streamlit UI with 4 tabs)
- src/ibkr_tax/services/tax_tooltips.py (KAP_TOOLTIPS and TAX_POOL_EXPLANATIONS created in Plan 26.1)
- docs/GERMAN_TAX_THEORY.md (full reference document created in Plan 26.1)

## Tasks

<task type="auto">
  <name>Add inline help text to Anlage KAP Report tab</name>
  <files>src/app.py</files>
  <action>
    In the existing "📊 Anlage KAP Report" tab (tabs[2]), add contextual help:

    1. Import `KAP_TOOLTIPS` from `ibkr_tax.services.tax_tooltips`
    2. After the report metrics are displayed (the `st.metric` calls in lines 200-209), add an expander section:
       ```python
       with st.expander("ℹ️ Was bedeuten diese Zeilen?"):
       ```
       Inside, display a concise explanation for each KAP line using the tooltip texts. Format as a clean table or list using `st.markdown`.

    3. Add `help=KAP_TOOLTIPS["kap_line_7"]` parameter to each `st.metric` call, so users see tooltips on hover. Example:
       ```python
       m1.metric("KAP Line 7 (Kapitalerträge)", f"{report.kap_line_7_kapitalertraege:,.2f} €", help=KAP_TOOLTIPS["kap_line_7"])
       ```

    DO NOT:
    - Change any calculation logic — this is purely a UI/presentation change
    - Reorder existing tabs — existing tab indices must remain stable
    - Remove any existing functionality
  </action>
  <verify>
    1. Launch Streamlit app: `uv run streamlit run src/app.py`
    2. Navigate to "Anlage KAP Report" tab
    3. Verify tooltip help icons appear on metric cards
    4. Verify "Was bedeuten diese Zeilen?" expander is visible below metrics
  </verify>
  <done>Metric cards have help tooltips, expander section shows line explanations</done>
</task>

<task type="auto">
  <name>Add new "📖 Tax Guide" tab to Streamlit UI</name>
  <files>src/app.py</files>
  <action>
    Add a 5th tab to the Streamlit app that renders a user-friendly summary of the German Tax Theory document.

    1. Update the `st.tabs` call to include a 5th tab:
       ```python
       tabs = st.tabs(["📁 Data Import", "⚙️ Tax Processing", "📊 Anlage KAP Report", "🗄️ Database Browser", "📖 Tax Guide"])
       ```

    2. In the new `tabs[4]` block, create a structured tax guide page:
       - Title: "📖 German Tax Guide for IBKR Users"
       - Introduction explaining what Anlage KAP is
       - Expandable sections for each topic area:
         - "Anlage KAP Lines Explained" (Lines 7-15 with descriptions)
         - "Tax Pool Separation (Verlusttöpfe)" (using TAX_POOL_EXPLANATIONS)
         - "FIFO Principle" (brief explanation)
         - "FX Conversion Rules" (ECB rates, weekend fallback)
         - "Corporate Actions" (splits, spinoffs)
         - "Options" (exercise/assignment/expiry)
       - Footer disclaimer: "This is not tax advice. Consult a Steuerberater."
       - Link to the full docs: st.markdown with a note that the full reference is in `docs/GERMAN_TAX_THEORY.md`

    3. Import `TAX_POOL_EXPLANATIONS` from `ibkr_tax.services.tax_tooltips`

    DO NOT:
    - Load the full markdown file into the UI — write a user-friendly summary instead
    - Change logic in other tabs
    - Break existing tab indices (tabs[0]-[3] must remain unchanged)
  </action>
  <verify>
    1. Launch Streamlit app: `uv run streamlit run src/app.py`
    2. Verify 5 tabs are visible
    3. Click "📖 Tax Guide" tab
    4. Verify all expandable sections render correctly
    5. Verify disclaimer is visible
  </verify>
  <done>5th tab "📖 Tax Guide" renders with expandable sections for all tax topics, disclaimer visible at bottom</done>
</task>

## Success Criteria
- [ ] Streamlit app now has 5 tabs (4th tab is Database Browser, 5th is Tax Guide)
- [ ] Report metrics in tab 3 have `help=` tooltips from KAP_TOOLTIPS
- [ ] Expander "Was bedeuten diese Zeilen?" appears below report metrics
- [ ] Tax Guide tab shows structured tax guidance with expandable sections
- [ ] No existing tests broken (run: `uv run pytest tests/ -x`)
- [ ] Visual verification via browser confirms all UI elements render correctly
