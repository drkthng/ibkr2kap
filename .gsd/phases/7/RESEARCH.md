# Phase 7 Research: FIFO Engine

## Objective
Design the FIFO matching engine to comply with German tax laws (strict chronological matching based on settlement dates).

## Discovery & Requirements

1. **Entities Involved**
   - `Trade`: The raw buy/sell transactions.
   - `FIFOLot`: Represents an open position. Only "BUY" trades (or Open positions depending on asset category) create FIFOLots.
   - `Gain`: The realized PnA event when a "SELL" trade matches against a `FIFOLot`.

2. **FIFO Logic (German Law)**
   - Strict chronological order based on `settle_date` (valuta).
   - Matching happens per `symbol` (or ISIN/WKN), though IBKR mostly uses `symbol`.
   - Asset categories matter (Stocks vs Options) because they might have different rules for opening/closing, though standard FIFO applies to the units.
   
3. **Currency Handling**
   - All tax calculations (cost basis, proceeds, PnL) MUST be in the base currency (EUR).
   - `cost_basis_total` in `FIFOLot` should be calculated using the EUR conversion rate at the time of the BUY trade.
   - `proceeds` in `Gain` should be calculated using the EUR conversion rate at the time of the SELL trade.
   - PnL = (Proceeds in EUR) - (Cost basis in EUR).

4. **Tax Pools (Ausblick)**
   - Stocks (STK) go to `Aktienveräußerungsgewinne/-verluste`.
   - Options (OPT) go to `Termingeschäfte` (losses capped at 20k, though SPEC says "without the 20k limit due to JStG 2024").
   - This phase focuses on the FIFO *matching* and PnL calculation; exact tax pool assignment can be basic for now and refined in Phase 8 (`Gain.tax_pool`).

## Architecture Decision
- Implement a `FIFOEngine` class or service in `src/ibkr_tax/services/fifo.py`.
- It will fetch all trades for an account, ordered by `settle_date`.
- Maintain a running state of open `FIFOLots` in the database.
- For a BUY: Create a new `FIFOLot`.
- For a SELL: Fetch open `FIFOLots` for the symbol, ordered by `settle_date` ASC. Deplete `remaining_quantity` iteratively. Create `Gain` records for each matched portion.
