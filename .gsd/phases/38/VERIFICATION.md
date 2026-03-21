# Phase 38 Verification: Termingeschäfte Reporting

## Must-Haves
- [x] **Schema Split**: `TaxReport` and `CombinedTaxReport` must include distinct gains and losses fields for Termingeschäfte.
  - **Verified**: Checked `src/ibkr_tax/schemas/report.py`.
- [x] **Aggregator Logic**: `TaxAggregatorService` must correctly split realized PnL for Termingeschäfte.
  - **Verified**: Ran `tests/test_tax_aggregator.py` (7/7 pass).
- [x] **Excel Export**: Summary sheet must show 3 distinct lines for Termingeschäfte.
  - **Verified**: Ran `tests/test_excel_export.py` (6/6 pass, verified row mapping).
- [x] **Streamlit UI**: UI must display 3 metrics (Netto, Gains, Losses) for Termingeschäfte.
  - **Verified**: Manual review of `src/app.py` update (3 columns metrics row).

## Verdict: PASS
Phase 38 is fully implemented and verified against all requirements.
