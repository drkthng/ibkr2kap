# Phase 4 Research: IBKR Flex Query XML Parser

## Discovery Level
Level 1: Quick Verification

## Objective
Use `ibflex` to parse the IBKR Flex Query XML files and map the extracted data to our Pydantic validation schemas (`AccountSchema`, `TradeSchema`, `CashTransactionSchema`).

## Findings
`ibflex` is already included in `pyproject.toml`.
Basic usage:
```python
from ibflex import parser
response = parser.parse(xml_file_path)
```

The parsed `response` contains a list of `FlexStatements`.
Inside a `FlexStatement`, we typically access:
- `statement.Trades` for trades.
- `statement.CashTransactions` for cash transactions.
- `statement.AccountId` for the account.

### Mapping to Pydantic Schemas

1.  **AccountSchema mapping:**
    *   `account_id`: `statement.AccountId`
    *   `currency`: `statement.BaseCurrency` (or a fixed "EUR" if we parse it differently but usually base currency).

2.  **TradeSchema mapping:**
    *   `ib_trade_id`: `trade.tradeID`
    *   `account_id`: `trade.accountId`
    *   `asset_category`: `trade.assetCategory`
    *   `symbol`: `trade.symbol`
    *   `description`: `trade.description`
    *   `trade_date`: `trade.tradeDate`
    *   `settle_date`: `trade.settleDateTarget`
    *   `currency`: `trade.currency`
    *   `fx_rate_to_base`: `trade.fxRateToBase`
    *   `quantity`: `trade.quantity`
    *   `trade_price`: `trade.tradePrice`
    *   `proceeds`: `trade.proceeds`
    *   `taxes`: `trade.taxes`
    *   `ib_commission`: `trade.ibCommission`
    *   `buy_sell`: `trade.buySell`
    *   `open_close_indicator`: `trade.openCloseIndicator`

3.  **CashTransactionSchema mapping:**
    *   `account_id`: `cash_tx.accountId`
    *   `symbol`: `cash_tx.symbol`
    *   `description`: `cash_tx.description`
    *   `date_time`: `cash_tx.dateTime`
    *   `settle_date`: `cash_tx.settleDate`
    *   `amount`: `cash_tx.amount`
    *   `type`: `cash_tx.type`
    *   `currency`: `cash_tx.currency`
    *   `fx_rate_to_base`: `cash_tx.fxRateToBase`
    *   `action_id`: `cash_tx.actionID`
    *   `report_date`: `cash_tx.reportDate`

**Notes:**
*   Some fields in `ibflex` might be slightly different named (e.g., `trade.fxRateToBase` vs `trade.fxRateToBase_`, we will check exact property names mapped by `ibflex` but mostly it uses the exact XML attributes converted to lowerCamelCase or matches exactly, e.g. `ibCommission`).
*   The Pydantic schemas handle data coercion correctly, but we must ensure we extract things as properly formatted strings/Decimals/dates before passing them to the Pydantic schemas.

## Next Steps
Proceed to create the execution plans for Phase 4.
