---
phase: 28
plan: 2
wave: 2
---

# Plan 28.2: Manual Position Entry UI (Streamlit Tab)

## Objective
Add a new "📝 Manual Positions" tab to the Streamlit UI allowing users to view, add, and delete manual cost-basis entries. Connect warnings in the Anlage KAP report to guide users to the new tab.

## Context
- .gsd/phases/28/RESEARCH.md
- src/app.py
- src/ibkr_tax/models/database.py (ManualPosition from Plan 28.1)
- src/ibkr_tax/db/repository.py

## Tasks

<task type="auto">
  <name>Add repository functions for ManualPosition CRUD</name>
  <files>src/ibkr_tax/db/repository.py</files>
  <action>
    Add three repository functions:

    1. `get_manual_positions(session, account_db_id) -> list[ManualPosition]`:
       Select all ManualPosition rows for the account, ordered by acquisition_date.

    2. `add_manual_position(session, account_db_id, symbol, asset_category, quantity, acquisition_date, cost_basis_total_eur, description) -> ManualPosition`:
       Create and commit a new ManualPosition record. Return the created object.

    3. `delete_manual_position(session, manual_position_id) -> bool`:
       Delete by ID. Return True if deleted.
  </action>
  <verify>
    `python -c "from ibkr_tax.db.repository import get_manual_positions, add_manual_position, delete_manual_position; print('OK')"`
  </verify>
  <done>Three repository functions importable and callable.</done>
</task>

<task type="auto">
  <name>Add "Manual Positions" tab to Streamlit app</name>
  <files>src/app.py</files>
  <action>
    1. Add new tab "📝 Manual Positions" to the tabs list (position 2, between "Tax Processing" and "Anlage KAP Report"):
       `tabs = st.tabs(["📁 Data Import", "⚙️ Tax Processing", "📝 Manual Positions", "📊 Anlage KAP Report", "🗄️ Database Browser", "📖 Tax Guide"])`

    2. Implement the new tab (at `tabs[2]`):
       - Header: "Manual Cost-Basis Entry"
       - Description: Explain purpose (for positions bought before XML data range).
       - **Account selection**: Dropdown (reusing `get_distinct_account_ids`).
       - **Existing positions table**: Use `st.dataframe` to show all manual positions for the selected account. Include columns: Symbol, Asset Category, Quantity, Acquisition Date, Cost Basis (EUR), Description.
       - **Delete button**: For each row, a delete action (use `st.form` or `st.button` with key).
       - **Add form** (`st.form`):
         - Symbol (text_input)
         - Asset Category (selectbox: STK, OPT, FUT, WAR)
         - Quantity (number_input, min_value=0.0001, step=1.0, format="%.4f")
         - Acquisition Date (date_input)
         - Cost Basis Total in EUR (number_input, min_value=0.01, step=0.01)
         - Description (text_input, default "Manual Opening Position")
         - Submit button → calls `add_manual_position` → `st.success`
       - **Important note**: After adding/deleting, user must re-run FIFO Engine to recalculate.

    3. In the Anlage KAP Report tab (warning section), add a hint:
       `st.info("💡 You can provide cost basis for these positions in the **📝 Manual Positions** tab.")`

    4. Adjust tab index references for existing tabs (Database Browser → tabs[4], Tax Guide → tabs[5]).
  </action>
  <verify>
    Start the app with `uv run streamlit run src/app.py` and visually confirm the new tab.
  </verify>
  <done>Manual Positions tab is functional: shows existing entries, allows adding via form, allows deleting, and warns to re-run FIFO.</done>
</task>

<task type="auto">
  <name>Write repository + integration tests</name>
  <files>tests/test_manual_positions.py</files>
  <action>
    Extend `tests/test_manual_positions.py` (from Plan 28.1 — append new tests):

    6. **test_add_manual_position_repository**: Call `add_manual_position`, then `get_manual_positions` → verify returned list has 1 item with correct fields.
    
    7. **test_delete_manual_position_repository**: Add a position, delete it → verify `get_manual_positions` returns empty list.
    
    8. **test_manual_position_eliminates_warning**: Create Account, ManualPosition (100 AAPL, cost 10000€), Trade SELL 50 AAPL. Run FIFORunner. Then run TaxAggregatorService.generate_report → verify `missing_cost_basis_warnings` is empty (no missing cost basis since manual position covers the sell).
  </action>
  <verify>
    `uv run pytest tests/test_manual_positions.py -v`
    `uv run pytest` (full regression)
  </verify>
  <done>All 8 tests in test_manual_positions.py pass. Full regression passes.</done>
</task>

## Success Criteria
- [ ] Repository functions for add/get/delete manual positions exist and work
- [ ] Streamlit UI has a new "Manual Positions" tab with form and table
- [ ] Anlage KAP warnings reference the Manual Positions tab
- [ ] All 8 unit tests pass
- [ ] Full regression suite passes (`uv run pytest`)
