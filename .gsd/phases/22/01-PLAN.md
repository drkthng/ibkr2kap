---
phase: 22
plan: 1
wave: 1
---

# Plan: UI and FX Bug Fixes

## Goal
Fix UI interruption and incorrect FX trade matching.

## Tasks

### Task 1: Fix Streamlit Interruption
Remove `st.stop()` from `src/app.py` to ensure all tabs render after a report is generated with warnings.
<task>
Modify `src/app.py` Tab 3 logic.
</task>
<verify>
Manual verification: Open Data Browser tab after generating a report with warnings.
</verify>

### Task 2: Exclude FX Trades from Standard FIFO
Filter out `asset_category == 'CASH'` in `FIFORunner` to ensure currency swaps are handled only by the FX engine.
<task>
Modify `src/ibkr_tax/services/fifo_runner.py`.
</task>
<verify>
Run unit tests and check if `CASH` trades create `FIFOLot` records.
</verify>

### Task 3: Detect Missing FX Cost Basis
Ensure the `TaxAggregatorService` also identifies unresolved FX disposals.
<task>
Update `src/ibkr_tax/services/tax_aggregator.py`.
</task>
<verify>
Add test case for missing FX acquisition.
</verify>
