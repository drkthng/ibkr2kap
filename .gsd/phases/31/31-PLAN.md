---
phase: 31
plan: 1
wave: 1
---

# Plan 31.1: Database Schema and Models

## Objective
Expand the `ManualPosition` model to store all relevant fields from the XML trades, so that manual entries can perfectly mirror ingested data, including support for closing trades.

## Context
- .gsd/SPEC.md
- src/ibkr_tax/models/database.py
- src/ibkr_tax/db/repository.py

## Tasks

<task type="auto">
  <name>Update ManualPosition model</name>
  <files>src/ibkr_tax/models/database.py</files>
  <action>
    Add the following columns to `ManualPosition`:
    - `trade_date` (String, nullable) - for backward compatibility we can continue using `acquisition_date` as `settle_date`. But let's add `trade_date`.
    - `currency` (String, nullable, default='EUR')
    - `fx_rate_to_base` (Numeric(18,6), nullable)
    - `trade_price` (Numeric(18,4), nullable)
    - `proceeds` (Numeric(18,4), nullable)
    - `taxes` (Numeric(18,4), nullable, default=0)
    - `ib_commission` (Numeric(18,4), nullable, default=0)
    - `buy_sell` (String, nullable) - e.g., "BUY" or "SELL"
    - `open_close_indicator` (String, nullable) - e.g., "O" or "C"
    
    Make `cost_basis_total_eur` nullable to support trades where it's calculated dynamically, though it can remain for legacy support.
  </action>
  <verify>pytest</verify>
  <done>ManualPosition model includes all the required fields.</done>
</task>

<task type="auto">
  <name>Update repository methods</name>
  <files>src/ibkr_tax/db/repository.py</files>
  <action>
    Update `add_manual_position` to accept all the new optional fields and save them to the model. Provide defaults of `None` for the new fields.
  </action>
  <verify>pytest</verify>
  <done>add_manual_position schema accepts the new fields.</done>
</task>

## Success Criteria
- [ ] Database automatically migrates successfully and includes the new columns on startup.
- [ ] The system can store newly provided manual position fields.

---
phase: 31
plan: 2
wave: 2
---

# Plan 31.2: Advanced Manual Entry UI

## Objective
Update the Streamlit interface to support entering all the new fields, matching the visual inputs requested by the user. Ensure prefill button intelligently flips "SELL" to "BUY" when filling an opening position.

## Context
- src/app.py

## Tasks

<task type="auto">
  <name>Update Manual Entry Form</name>
  <files>src/app.py</files>
  <action>
    Modify `app.py` under the "Manual Positions" tab:
    - Add inputs for `Buy/Sell`, `Open/Close`, `Currency`, `FX Rate`, `Trade Price`, `Proceeds`, `Commissions`, `Taxes`.
    - If `Buy/Sell` is provided, calculate the underlying metrics dynamically or just pass them raw to the backend.
    - Pre-fill values mapping from the warning (e.g., if a matching closing SELL trade is chosen, prefill BUY and O).
    - Call `add_manual_position` with the new fields.
  </action>
  <verify>pytest</verify>
  <done>UI displays matching fields for an IBKR trade.</done>
</task>

## Success Criteria
- [ ] Users can enter close/open trades manually with all granular data.
- [ ] Prefill correctly defaults to the inverse direction (Close -> Open).

---
phase: 31
plan: 3
wave: 3
---

# Plan 31.3: FIFO Engine Integration

## Objective
Update the FIFO execution path so that manual positions with `buy_sell` provided are treated identically to trades.

## Context
- src/ibkr_tax/services/fifo_runner.py
- src/ibkr_tax/services/fifo.py

## Tasks

<task type="auto">
  <name>Process Manual Position as Trade</name>
  <files>src/ibkr_tax/services/fifo_runner.py</files>
  <action>
    Update `_process_manual_position`:
    - If `mp.buy_sell` is filled, duck-type or convert it to a `Trade` object in memory:
      `mock_trade = Trade(id=1000000+mp.id, symbol=mp.symbol, asset_category=mp.asset_category, quantity=mp.quantity, ...)`
    - Feed it directly into `fifo_engine.process_trade(mock_trade)`.
    - If it's a legacy position without `buy_sell`, fall back to injecting the raw `FIFOLot`.
  </action>
  <verify>pytest</verify>
  <done>Manual closes correctly match against existing inventory.</done>
</task>

## Success Criteria
- [ ] Closing trades entered manually match against valid opening inventory.
- [ ] FIFO logic processes these synthetic trades identically to XML trades.
