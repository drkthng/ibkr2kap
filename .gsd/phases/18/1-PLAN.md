---
phase: 18
plan: 1
wave: 1
---

# Plan 18.1: Add Buy-Date to Gains Detail Excel Sheet

## Objective
Surface the original buy-date (acquisition date) alongside the existing sell-date for every realised
gain/loss row in the "Gains Detail" Excel sheet.  The buy-date is already stored in the database —
`Gain.buy_lot` → `FIFOLot.settle_date` — so no schema migration is required; this is purely a
presentation change in the Excel export layer.

## Context
- .gsd/SPEC.md
- src/ibkr_tax/services/excel_export.py
- src/ibkr_tax/models/database.py  (Gain / FIFOLot models)
- tests/test_excel_export.py

## Tasks

<task type="auto">
  <name>Add "Anschaffungsdatum" column to Gains Detail sheet</name>
  <files>src/ibkr_tax/services/excel_export.py</files>
  <action>
    1. In the `detail_headers` list (line 72), insert a new column **"Anschaffungsdatum"** as the
       second header (index 1), shifting existing columns right.
       New header order:
       `["Verkaufsdatum", "Anschaffungsdatum", "Symbol", "Tax Pool", "Quantity",
        "Proceeds (EUR)", "Cost Basis (EUR)", "Gain/Loss (EUR)"]`
       (Also rename the existing "Datum" header to "Verkaufsdatum" for clarity.)
    2. In the per-row loop (around line 98), populate the new column with
       `g.buy_lot.settle_date`.
       Use eager loading (joinedload) on `Gain.buy_lot` in the query to avoid N+1 queries, or
       rely on the existing lazy load since data volumes are small — either is acceptable.
    3. Adjust column width list to include the new column.
    - Do NOT change Sheet 1 ("Anlage KAP Summary") or Sheet 3 ("Währungsgewinne").
    - Do NOT change any model or schema files.
  </action>
  <verify>python -m pytest tests/test_excel_export.py -v</verify>
  <done>
    - The "Gains Detail" sheet has 8 columns (was 7).
    - Column A = "Verkaufsdatum", Column B = "Anschaffungsdatum".
    - Each data row populates both date columns correctly.
  </done>
</task>

<task type="auto">
  <name>Update and extend Excel export tests</name>
  <files>tests/test_excel_export.py</files>
  <action>
    1. Update `test_gains_detail_sheet_row_count`:
       - Test fixtures must create real `FIFOLot` records so that `g.buy_lot.settle_date` is
         resolvable (currently `buy_lot_id` is set to bare ints like 1, 2 with no matching lot).
         Create proper FIFOLot rows linked to the buy-trades, then reference those IDs in the
         Gain rows.
       - Assert that the new second column contains the buy lot's settle_date.
    2. Update `test_gains_detail_sorted_by_date`:
       - Similarly create real `FIFOLot` records.
       - Assert column B values are the expected buy-dates.
    3. Add a new test `test_gains_detail_buy_date_column`:
       - Creates two gains with different buy-dates and verifies:
         (a) Header row column B is "Anschaffungsdatum"
         (b) Data rows column B contain the correct FIFOLot.settle_date values.
    - Verify ALL old tests still pass (no regressions on summary or FX sheets).
  </action>
  <verify>python -m pytest tests/test_excel_export.py -v</verify>
  <done>
    - All tests in test_excel_export.py pass.
    - At least one test explicitly asserts the "Anschaffungsdatum" header and cell values.
  </done>
</task>

## Success Criteria
- [ ] `python -m pytest tests/test_excel_export.py -v` — all tests pass (0 failures)
- [ ] Gains Detail sheet has 8 columns with "Anschaffungsdatum" as column B
- [ ] No changes to database models, schemas, or other services
