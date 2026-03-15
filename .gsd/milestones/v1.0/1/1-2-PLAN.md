---
phase: 1
plan: 2
wave: 2
---

# Plan 1.2: Tax Calculation Models (FIFOLot, Gain)

## Objective
Establish the models needed to execute chronological, FIFO-based matchings across tax years and track realized gains categorized correctly.

## Context
- .gsd/SPEC.md
- src/ibkr_tax/models/database.py

## Tasks

<task type="auto">
  <name>Implement FIFOLot Model</name>
  <files>src/ibkr_tax/models/database.py</files>
  <action>
    - Create a `FIFOLot` model tracking open/working units for assets from BUYs.
    - Important fields: `id`, `trade_id` (Foreign Key referencing the origin `Trade`), `asset_category`, `symbol`, `settle_date` (critical for tax year assignment), `original_quantity` (Numeric), `remaining_quantity` (Numeric), `cost_basis_total` (Numeric), `cost_basis_per_share` (Numeric).
    - Ensure accurate foreign key linkage to the originating `Trade`.
  </action>
  <verify>python -c "from ibkr_tax.models.database import FIFOLot"</verify>
  <done>FIFOLot model successfully created, mapped to Trade.</done>
</task>

<task type="auto">
  <name>Implement Gain Model</name>
  <files>src/ibkr_tax/models/database.py</files>
  <action>
    - Create a `Gain` model tracking the realized tax effects of SELL events. 
    - Important fields: `id`, `sell_trade_id` (ForeignKey to the SELL `Trade`), `buy_lot_id` (ForeignKey to the `FIFOLot`), `quantity_matched` (Numeric), `tax_year` (Integer - derived from settle_date), `proceeds` (Numeric), `cost_basis_matched` (Numeric), `realized_pnl` (Numeric), `tax_pool` (String Enum: Aktienverrechnungstopf, Termingeschäfte, Sonstige).
    - Map the loss/gain pools per constraints.
  </action>
  <verify>python -c "from ibkr_tax.models.database import Gain"</verify>
  <done>Gain model correctly relates back to Trade and FIFOLot with correct tax_pool structure.</done>
</task>

<task type="auto">
  <name>Add Schema Tests</name>
  <files>tests/test_db_setup.py</files>
  <action>
    - Add unit tests verifying `Base.metadata.create_all()` succeeds effectively with these new models.
    - Write a basic test inserting an Account, Trade, FIFOLot, Dividend, and Gain ensuring exact precision and valid relational keys.
  </action>
  <verify>pytest -v tests/test_db_setup.py</verify>
  <done>Test succeeds showing all tables setup properly without foreign key clashes.</done>
</task>

## Success Criteria
- [ ] FIFOLot and Gain models track the necessary chronological basis mechanisms.
- [ ] All database schemas correctly apply and pass `pytest` verification.
