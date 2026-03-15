# Phase 5 Research: IBKR CSV Activity Statement Parser

IBKR CSV Activity Statements do not follow a flat table structure. Instead, they use a multi-section structure where each line has a section identifier in the first column, a row type in the second ("Header", "Data", "SubTotal", "Total", etc.), and then the actual data fields.

## Key Sections for Tax Parsing
- **Trades**: Represents execution of buy/sell orders.
- **Cash Report** or **Dividends** / **Withholding Tax**: Represents cash transactions.
- **Statement of Funds**: Detailed transaction ledger.
- **Account Information**: Base currency and account ID.

## Implementation Approach
1. **Built-in CSV Module**: Python's `csv` module is sufficient for parsing the raw structure.
2. **Filtering strategy**: Iterate row by row. Keep track of the 'Header' row for each section to map indices to field names. If `row[0] == section` and `row[1] == 'Data'`, build a dictionary from the headers and map the fields.
3. **Pydantic Validation**: Map the extracted dictionaries into the existing `TradeSchema` and `CashTransactionSchema` defined in Phase 2.
4. **Resiliency**: Ensure parsing gracefully ignores unneeded sections and handles missing optional columns.
