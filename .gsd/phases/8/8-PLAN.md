---
phase: 8
plan: 1
wave: 1
---

# Plan 8.1: Tax Report Aggregation

## Objective
Implement the logic to aggregate `Gain` and `CashTransaction` records into a dedicated `TaxReport` schema. This prepares the exact data structure needed to populate the "Anlage KAP" columns (e.g. Lines 7, 8, 9, 10, 15) for German tax reporting. Since the `FIFOEngine` already assigns `tax_pool`, this service focuses purely on querying and aggregation per `account_id` and `tax_year`.

## Context
- .gsd/SPEC.md
- .gsd/phases/8/RESEARCH.md
- src/ibkr_tax/models/database.py
- src/ibkr_tax/services/fifo.py

## Tasks

<task type="auto">
  <name>Create TaxReport Schema</name>
  <files>src/ibkr_tax/schemas/report.py</files>
  <action>
    Create a Pydantic model `TaxReport` strictly representing the aggregated tax pools for a given year.
    Include fields (all `Decimal` with strict validation):
    - `kap_line_7_kapitalertraege`: Sum of Dividends, Interest, and 'Sonstige' gains.
    - `kap_line_8_gewinne_aktien`: Sum of positive gains from 'Aktien'.
    - `kap_line_9_verluste_aktien`: Sum of absolute negative gains from 'Aktien'.
    - `kap_line_10_termingeschaefte`: Net sum of gains/losses from 'Termingeschäfte'.
    - `kap_line_15_quellensteuer`: Sum of 'Withholding Tax' from CashTransactions.
    - `total_realized_pnl`: Sum of all realized PnL.
  </action>
  <verify>uv run pytest tests/</verify>
  <done>Schema parses exact decimals correctly without rounding errors, providing initialized 0 defaults.</done>
</task>

<task type="auto">
  <name>Implement TaxAggregatorService</name>
  <files>src/ibkr_tax/services/tax_aggregator.py</files>
  <action>
    Create `TaxAggregatorService(session)`.
    Implement `generate_report(account_id: int, tax_year: int) -> TaxReport`.
    - Query `Gain` by `account_id` (via `sell_trade`) and `tax_year`.
    - Query `CashTransaction` by `account_id` and `tax_year` (derived from `settle_date[:4]`).
    - Aggregate amounts grouped by the fields mapped in `TaxReport`.
    - Ensure all aggregations correctly sum `Decimal` types avoiding precision drift.
  </action>
  <verify>uv run pytest tests/</verify>
  <done>Service executes without failing and properly instantiates the `TaxReport` output model.</done>
</task>

<task type="auto">
  <name>Write Aggregation Tests</name>
  <files>tests/test_tax_aggregator.py</files>
  <action>
    Write unit tests for `TaxAggregatorService`.
    - Seed the database with known `Gain` and `CashTransaction` records for different tax pools across multiple tax years (e.g., year 2023, 2024).
    - Call `generate_report` for a specific year and assert the exactly expected numeric values for kap lines.
    - Ensure zero amounts are returned when no records exist.
  </action>
  <verify>uv run pytest tests/test_tax_aggregator.py -v</verify>
  <done>All tests pass capturing exact decimal summations across categories.</done>
</task>

## Success Criteria
- [ ] TaxReport Pydantic schema is fully typed using Decimals.
- [ ] Aggregator correctly sums 'Aktien' gains (positive) vs 'Aktien' losses (negative, absolute).
- [ ] Termingeschäfte net correctly.
- [ ] Dividends and Withholding taxes are extracted from CashTransactions.
- [ ] 100% of aggregation tests pass.
