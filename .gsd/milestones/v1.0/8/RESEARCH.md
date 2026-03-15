# Phase 8: Tax Categorization Research

## Current State Analysis
1. **Database Models**: 
   - `Gain` model already includes a `tax_pool` column (String).
   - `CashTransaction` model tracks dividends, withholding taxes, interest, etc. with a `type` column.
2. **FIFO Engine**:
   - `src/ibkr_tax/services/fifo.py` already includes `_determine_tax_pool(trade)` which accurately assigns `'Aktien'`, `'Termingeschäfte'`, or `'Sonstige'` based on `asset_category` (`STK`, `OPT`/`FUT`, otherwise `Sonstige`).

## Gap Analysis & Phase 8 Requirements
Since the data is already categorized at the granular (per-lot) level, Phase 8 needs to implement the **Aggregation and Netting** logic required to produce the final numbers for the tax return (Anlage KAP).

German tax law specifies different rules for offsetting losses (Verlustverrechnungskreise):
- **Aktienverlusttopf**: Losses from stock sales (`Aktien`) can only be offset against gains from stock sales.
- **Termingeschäfte**: Gains and losses from options/futures (`Termingeschäfte`). Per JStG 2024, the 20k EUR limit is removed, making it purely a separate netting pool (or netted against Sonstige).
- **Allgemeiner Topf (Sonstige)**: Dividends, interest, and other gains.

For **Anlage KAP** (using typical line mapping for foreign brokers, e.g. Lines 19-24, or standard Lines 7, 8, 9, 10, 15 as requested in SPEC):
- **Line 7 (Kapitalerträge)**: Sum of Dividends, Interest, and `Sonstige` Gains.
- **Line 8 (Gewinne aus Aktien)**: Sum of all positive `Gain.realized_pnl` where `tax_pool == 'Aktien'`.
- **Line 9 (Verluste aus Aktien)**: Sum of all negative `Gain.realized_pnl` where `tax_pool == 'Aktien'`. 
   - *Note: Some tools net these first. We should provide both the raw aggregated gains/losses and the netted values.*
- **Line 10 (Termingeschäfte)**: Net of all `Gain.realized_pnl` where `tax_pool == 'Termingeschäfte'`.
- **Line 15 (Quellensteuer)**: Sum of `CashTransaction.amount` where `type == 'Withholding Tax'`.

## Architecture Recommendation for Phase 8
1. Create a `TaxAggregatorService` or `TaxReportService` in `src/ibkr_tax/services/tax_aggregator.py`.
2. Implement a method `generate_tax_report(account_id: int, tax_year: int) -> dict` (or a Pydantic model `TaxReport`).
3. The service will query `Gain` and `CashTransaction` for the given `account_id` and `tax_year`.
4. Return an aggregated data structure grouping by the Anlage KAP categories.

## Plan Structure (8-PLAN.md)
Will include:
- **Task 1**: Create `TaxReport` Pydantic schema for the output.
- **Task 2**: Create `TaxAggregatorService` with aggregation logic.
- **Task 3**: Create corresponding tests `test_tax_aggregator.py`.
