## Phase 8 Verification: Tax Categorization

### Must-Haves
- [x] Tax categorization engine for mapping to "Anlage KAP" — VERIFIED
  - Evidence: `TaxAggregatorService` correctly groups gains/losses from `Gain` model and cash events from `CashTransaction` into the specific Anlage KAP lines (7, 8, 9, 10, 15) as specified in the `TaxReport` schema.
  - Test Result: `tests/test_tax_aggregator.py::test_generate_report_with_mixed_data` PASSED with exact decimal matching.

### verdict: PASS
