---
phase: 34
plan: 1
wave: 1
---
# 34-1: Aggregator Discrepancy & UI Cleanup

## Goals
1. Fix the case-sensitivity bug in `TaxAggregatorService` for Payment in Lieu of Dividends.
2. Add `Bond Interest Received` to Kapitalerträge.
3. Remove `Total Trading Costs` from the Manual Entry UI.

## Tasks
1. [ ] Remove `Trading Costs` input from `app.py`.
2. [ ] Update `TaxAggregatorService.py` with case-insensitive matching for dividends/interest.
3. [ ] Update `TaxAggregatorService.py` to include `Bond Interest Received`.
4. [ ] Run unit tests to verify aggregation results.
