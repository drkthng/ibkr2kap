---
phase: 36
plan: 2
wave: 2
---

# 02-UI-EXCEL-PLAN: UI and Excel Export Remodel

## Goal
Update the Streamlit UI and Excel export summary sheet to display the new tax-pool-aligned metrics and remove the misleading combined total.

## Tasks

### T1: Remodel Excel Summary Sheet
**File:** [excel_export.py](file:///d:/Antigravity/IBKR2KAP/src/ibkr_tax/services/excel_export.py)
- Update `_add_summary_sheet` to include the new Sections (Anlage KAP lines, Anlage SO, and Zusammenfassung nach Verlusttöpfen).
- Remove "Gesamt Realisierter Kursgewinn" row.

### T2: Remodel Streamlit UI Metrics
**File:** [app.py](file:///d:/Antigravity/IBKR2KAP/src/app.py)
- Update the metrics display in Tab 4 (Anlage KAP Report).
- Remove `total_realized_pnl` metric.
- Add "Aktientopf (Netto)" and "Allgemeiner Topf" metrics.
- Keep "Anlage SO (FX)" as a standalone summary.

### T3: Update Tests
**Files:**
- `tests/test_tax_aggregator.py`
- `tests/test_excel_export.py`
- Update all assertions to match the new schema and summary fields.

## Verification
- `uv run pytest tests/test_tax_aggregator.py tests/test_excel_export.py -v`
- Full suite: `uv run pytest -v`
