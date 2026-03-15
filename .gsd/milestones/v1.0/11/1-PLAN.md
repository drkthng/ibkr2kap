---
phase: 11
plan: 1
wave: 1
---

# Plan 11.1: Excel Export Service

## Objective
Create `ExcelExportService` in `src/ibkr_tax/services/excel_export.py` that accepts a `TaxReport` and produces a formatted `.xlsx` file suitable for handing to a German tax consultant. The output must be human-readable, formatted for Anlage KAP lines (7, 8, 9, 10, 15), and include a detail sheet with individual gains and cash transactions.

`openpyxl` is **already a declared dependency** in `pyproject.toml` (no install step needed).

## Context
- `.gsd/SPEC.md`
- `src/ibkr_tax/schemas/report.py` — `TaxReport` (the aggregated data to export)
- `src/ibkr_tax/models/database.py` — `Gain`, `Trade`, `CashTransaction` (detail rows)
- `src/ibkr_tax/services/tax_aggregator.py` — reference for how data is fetched

## Tasks

<task type="auto">
  <name>Implement ExcelExportService</name>
  <files>src/ibkr_tax/services/excel_export.py</files>
  <action>
    Create the file `src/ibkr_tax/services/excel_export.py` with the following class:

    ```python
    class ExcelExportService:
        def __init__(self, session: Session):
            self.session = session

        def export(self, report: TaxReport, output_path: str) -> None:
            ...
    ```

    The `export` method must:

    1. **Create a Workbook with two sheets:**

       **Sheet 1 — "Anlage KAP Summary"**
       - Row 1: Title row: "IBKR2KAP — Anlage KAP Bericht" merged across columns A–C, bold, font size 14
       - Row 2: "Konto: {report.account_id}" / "Steuerjahr: {report.tax_year}"
       - Row 3: blank separator
       - Rows 4–9: A 3-column table (Zeile | Bezeichnung | Betrag in EUR):
         | Zeile | Bezeichnung                            | Betrag (EUR) |
         |-------|----------------------------------------|--------------|
         | 7     | Kapitalerträge (Dividenden / Sonstige) | {kap_line_7} |
         | 8     | Gewinne aus Aktienveräußerungen        | {kap_line_8} |
         | 9     | Verluste aus Aktienveräußerungen       | {kap_line_9} |
         | 10    | Termingeschäfte (netto)                | {kap_line_10}|
         | 15    | Anrechenbare ausländische Steuern      | {kap_line_15}|
         |       | Gesamt realisierter Gewinn/Verlust     | {total_pnl}  |
       - Header row must be bold with a grey fill (`PatternFill`).
       - Monetary values must be formatted as `#,##0.00 €` using `number_format`.
       - Column widths: A=8, B=42, C=18.
       - Negative kap_line_10 values must still display (net figure — can be negative).

       **Sheet 2 — "Gains Detail"**
       - Header row: Date | Symbol | Tax Pool | Quantity | Proceeds (EUR) | Cost Basis (EUR) | Gain/Loss (EUR)
       - One row per `Gain` record for the given `account_id` and `tax_year`.
       - Join through `Gain → sell_trade → Trade` to get: `settle_date`, `symbol`.
       - Monetary columns formatted as `#,##0.00 €`, quantity as `#,##0.0000`.
       - Freeze the header row (`freeze_panes="A2"`).
       - Sort rows by `settle_date` ascending.

    2. **Save the workbook** to `output_path` using `workbook.save(output_path)`.

    **Imports needed:**
    ```python
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    from openpyxl.utils import get_column_letter
    from sqlalchemy.orm import Session
    from sqlalchemy import select
    from ibkr_tax.schemas.report import TaxReport
    from ibkr_tax.models.database import Gain, Trade, Account
    ```

    **Do NOT:**
    - Use pandas; only openpyxl.
    - Use floats anywhere; all amounts already come in as `Decimal` — write them as-is (openpyxl accepts Decimal natively).
    - Leave `output_path` creation to the caller; the service just writes — caller must ensure the directory exists.
  </action>
  <verify>python -c "from ibkr_tax.services.excel_export import ExcelExportService; print('OK')"</verify>
  <done>
    - `src/ibkr_tax/services/excel_export.py` exists and imports cleanly.
    - Class has `__init__(self, session)` and `export(self, report, output_path)`.
    - No floats used, no pandas import.
  </done>
</task>

## Success Criteria
- [ ] `ExcelExportService` importable from `ibkr_tax.services.excel_export`
- [ ] `export()` creates a valid `.xlsx` at `output_path`
- [ ] Sheet 1 ("Anlage KAP Summary") contains all 5 KAP lines + total
- [ ] Sheet 2 ("Gains Detail") contains one row per matched Gain
- [ ] No float math; all Decimal values preserved
