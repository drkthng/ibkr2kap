# Phase 9 Research: Options Edge Cases

## Objective
Handle complex but crucial mechanisms around options: expirations, assignments, and exercises modifying stock basic costs.

## Background
According to German tax law and general accounting principles, when an option is exercised or assigned, the premium of the option must be factored into the cost basis or proceeds of the resulting stock transaction. 

### Scenarios
1. **Long Call Exercise**: Buy underlying at strike. Cost basis of stock = Strike price + Call Premium Paid.
2. **Short Call Assignment**: Sell underlying at strike. Proceeds of stock = Strike price + Call Premium Received.
3. **Long Put Exercise**: Sell underlying at strike. Proceeds of stock = Strike price - Put Premium Paid.
4. **Short Put Assignment**: Buy underlying at strike. Cost basis of stock = Strike price - Put Premium Received.
5. **Expiration**: The option expires worthless. The premium paid (Long) is a realized loss, or the premium received (Short) is a realized gain. (Categorized into Termingeschäfte).

## IBKR Data Structure
In the IBKR Flex Query XML (parsed by `ibflex`):
- Expirations, Assignments, and Exercises are logged in `<OptionEAE>` or `<CorporateActions>` / `<Trades>` with specific `transactionType` or `notes` (e.g., `A` for assignment, `E` for exercise).
- `ibflex.OptionEAE` contains: `transactionType` (OptionAction Enum), `symbol`, `underlyingSymbol`, `strike`, `putCall`, `quantity`, `tradePrice`, etc.
- A simultaneous underlying stock `<Trade>` is generated at the strike price.

## Necessary Changes
1. **Schema & Models**: 
   - We may not need a persistent `OptionEAE` DB table if we process them directly during the import or FIFO phase. However, tracking them in a staging table or modifying `Trade` elements before FIFO matching is required. 
   - Alternatively, `OptionEAE` can be parsed and passed to the FIFO engine to map the "closing" of the option lot to the "opening/closing" of the stock lot.
2. **Parser Updates**:
   - `ibkr_tax.schemas.ibkr` needs an `OptionEAE` schema.
   - `ibkr_tax.services.flex_parser` must extract `OptionEAE`.
   - `ibkr_tax.services.csv_parser` must extract `OptionEAE`.
3. **Core Logic (FIFO & Options)**:
   - When an Option Exercise/Assignment occurs, find the open `FIFOLot` for that option.
   - Close the option `FIFOLot` (mark remaining_quantity = 0).
   - Transfer its `cost_basis_total` to the corresponding underlying stock's `Trade` before/during stock FIFO processing.
   - Expirations simply close the `FIFOLot` and realize a Gain/Loss immediately in the `Termingeschäfte` pool.

## Strategy
- **Plan 9.1**: Schema & Parser updates (Ingest OptionEAE).
- **Plan 9.2**: Option Engine / FIFO Integration (Adjust stock cost basis/proceeds).
- **Plan 9.3**: Tests & Verification (Verify all 5 scenarios).
