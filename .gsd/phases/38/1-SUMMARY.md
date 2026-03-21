# Summary: Plan 38.1 - Termingeschäfte Granular Reporting

## Accomplishments
- **Schema Update**: Added `kap_termingeschaefte_gains` and `kap_termingeschaefte_losses` to `TaxReport` and `CombinedTaxReport` in `src/ibkr_tax/schemas/report.py`.
- **Aggregator Logic**: Modified `TaxAggregatorService` in `src/ibkr_tax/services/tax_aggregator.py` to calculate positive and negative PnL separately for the `Termingeschäfte` pool.
- **Excel Export**: Updated `ExcelExportService` in `src/ibkr_tax/services/excel_export.py` to include extra rows for Gains and Losses beneath the netted Line 10 in the summary sheet.
- **Streamlit UI**: Updated `src/app.py` to display three separate metrics for Termingeschäfte (Netto, Gains, Losses) in the Summary tab and account details.
- **Testing**: Updated and verified `tests/test_tax_aggregator.py` and `tests/test_excel_export.py` to ensure correct field values and layout.

## Verification Results
- `tests/test_tax_aggregator.py`: 7/7 passing (verified split logic).
- `tests/test_excel_export.py`: 6/6 passing (verified Excel row inclusion).
- `pytest`: Full suite verified with no regressions (tested via separate logs).
