# Phase 14 Research: Foreign Currency Gains (§ 23 EStG)

## 1. Problem Statement
German tax law dictates that foreign currency holdings (like USD) are treated as assets. Realized exchange rate gains and losses are taxable as private sales transactions ("Private Veräußerungsgeschäfte") under § 23 EStG (Einkommensteuergesetz) if the holding period between acquisition and disposal is 1 year or less. If held for more than 1 year, the gains are tax-free. 
The matching of acquisition and disposal must follow the FIFO (First-In, First-Out) principle.

## 2. Triggers for Acquisition and Disposal
**Acquisition of Foreign Currency (e.g., USD):**
- Direct FX Conversion: Buying USD with EUR
- Selling an asset: Selling a US stock where proceeds are credited in USD
- Income: Receiving dividends or interest in USD

**Disposal of Foreign Currency (e.g., USD):**
- Direct FX Conversion: Selling USD for EUR
- Buying an asset: Using USD to buy a US stock
- Expenses: Paying fees, withholding taxes, or interest in USD

## 3. Current Limitations
Currently, `Trade`, `CashTransaction`, `FIFOLot`, and `Gain` models track the PnL of the *assets* (stocks, options). They convert the foreign currency amounts to EUR at the time of the transaction.
However, there is no tracker for the "pool of USD" itself.

## 4. Architectural Decision
To implement this without breaking existing logic, we must introduce a **separate FIFO engine for foreign currency**:
1. **New Models:** `FXFIFOLot` (tracks available USD and its EUR cost basis) and `FXGain` (tracks the realized PnL and the 1-year holding period flag).
2. **FX FIFO Engine:** A new service `FXFIFOEngine` that scans all transactions chronologically (Trades, CashTransactions, CorporateActions if applicable) and builds FX lots and matches them.
3. **Holding Period Logic:** When matching a disposal to an acquisition lot, calculate `days_held`. If `days_held <= 365`, `is_taxable = True`.
4. **Tax Aggregation:** `TaxAggregatorService` needs to sum up the taxable `FXGain`s. According to German tax law, these go into the "Sonstige Einkünfte" (Anlage SO) or are declared under a specific line if treated as Anlage KAP, but usually § 23 is Anlage SO. Wait, the spec says "Address §23 EStG ... Marked as highly optional". The Excel Export will need a new sheet or section for "Foreign Currency Gains (§ 23 EStG)".

## 5. Implementation Steps (Execution Waves)
**Wave 1: Foundation**
- Update `database.py` with `FXFIFOLot` and `FXGain` models.
- Add Pydantic schemas if needed.

**Wave 2: Core Logic**
- Implement `FXFIFOEngine` to process a chronological stream of all USD cash flows (Trades & CashTransactions).

**Wave 3: Integration & Export**
- Integrate the engine into the main data pipeline runner.
- Update `ExcelExportService` to include an FX Gains report tab.
