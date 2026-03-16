# Flex Query Setup – Step-by-Step Guide

## 1. Navigation to the Flex Query Builder

1. **Login:** [https://portal.interactivebrokers.com](https://portal.interactivebrokers.com)
2. **Menu:** Performance & Reports → Flex Queries
3. Click the **[+]** button under "Activity Flex Queries"
4. *(NOT "Trade Confirmation Flex Query" – that is something else!)*

## 2. Basic Settings

| Setting | Value |
| :--- | :--- |
| **Query Name** | `IBKR2KAP_Full_Export` |
| **Date Period** | `Last 365 Calendar Days` |
| **Format** | `XML` |
| **Delivery** | `Online (Download)` |
| **Include canceled trades** | ☐ No |
| **Include audit trail** | ☐ No |
| **Include Cost Basis in Pos** | ☑ Yes |

> **IMPORTANT:** Because IBKR limits Flex Queries to a maximum of 365 days, you will need to execute this query multiple times to cover your entire trading history. See the **Recommended Export Strategy** below.

## 3. Sections and Fields – Exactly What You Need

In the Flex Query Builder, you will see a list of Sections. You can select individual fields for each Section. Here is exactly what you need to activate:

### ✅ Section 1: Trades (CRITICAL)

This is the most important section. Click on "Trades", then select the following fields:

**Identification:**

| Field | Do we need it? | Why |
| :--- | :---: | :--- |
| TradeID | ✅ | Unique ID, deduplication |
| IBOrderID | ✅ | Matching related trades |
| IBExecID | ☑️ | Helpful for debugging |

**Instrument:**

| Field | Do we need it? | Why |
| :--- | :---: | :--- |
| Symbol | ✅ | Ticker symbol |
| Description | ✅ | Full name |
| AssetCategory | ✅ | STK, OPT, FUT, CASH – for tax pool assignment |
| ISIN | ✅ | International identifier, tax consultant needs this |
| UnderlyingSymbol | ✅ | For options: underlying stock |
| UnderlyingListingExchange | ☐ | Optional |
| Multiplier | ✅ | For options: usually 100 |
| Strike | ✅ | For options: strike price |
| Expiry | ✅ | For options: expiration date |
| Put/Call | ✅ | P or C |
| SecurityID | ☑️ | Alternative ID |
| SecurityIDType | ☑️ | e.g. "ISIN" |
| CUSIP | ☐ | US-specific, not needed |
| FIGI | ☐ | Optional |
| ConID | ☑️ | IBKR Contract ID, helpful for matching |

**Trade Details:**

| Field | Do we need it? | Why |
| :--- | :---: | :--- |
| DateTime | ✅ | Time of trade |
| TradeDate | ✅ | Trade date |
| SettleDateTarget | ✅ | CRITICAL! Determines the tax year! |
| Buy/Sell | ✅ | Buy or Sell |
| Quantity | ✅ | Quantity |
| TradePrice | ✅ | Price |
| Proceeds | ✅ | Proceeds |
| IBCommission | ✅ | Fees |
| IBCommissionCurrency | ✅ | Currency of the fees |
| NetCash | ✅ | Net cash flow |
| Currency | ✅ | Trading currency |
| FXRateToBase | ✅ | IBKR's exchange rate (for comparison, we use ECB) |
| CostBasis | ☑️ | IBKR's calculation (for comparison, we calculate ourselves) |
| RealizedPnL | ☑️ | IBKR's calculation (for comparison) |
| TransactionType | ✅ | ExchTrade, BookTrade, etc. |
| OrderType | ☐ | Not tax-relevant |
| LevelOfDetail | ✅ | Set to "EXECUTION" |

### ✅ Section 2: Cash Transactions (DIVIDENDS + INTEREST)

In some IBKR portal versions, these are separate "Dividends" and "Interest" sections. In the Flex Query, they are often combined under "Cash Transactions".

| Field | Do we need it? | Why |
| :--- | :---: | :--- |
| DateTime | ✅ | When it was paid |
| Symbol | ✅ | Which stock |
| ISIN | ✅ | Identifier |
| Description | ✅ | Contains details like "Cash Dividend 0.25 USD per Share" |
| Amount | ✅ | Amount |
| Currency | ✅ | Currency |
| Type | ✅ | IMPORTANT! Dividends, Payment In Lieu Of Dividends, Bond Interest, etc. |
| FXRateToBase | ✅ | For comparison |
| ReportDate | ✅ | For tax year assignment |
| SettleDate | ✅ | For tax year assignment |
| ActionID | ☑️ | For mapping to withholding tax |

> **Watch out:** "Payment in Lieu of Dividends" are substitute payments (when your shares were lent out) and face different tax logic!

### ✅ Section 3: Corporate Actions

| Field | Do we need it? | Why |
| :--- | :---: | :--- |
| DateTime | ✅ | Time |
| Symbol | ✅ | Affected stock |
| ISIN | ✅ | |
| Description | ✅ | CRITICAL! Contains Split-Ratio, Merger details |
| ActionType | ✅ | SO (Split), TC (Tender), FS (Forward Split), etc. |
| Quantity | ✅ | New quantity |
| Value | ✅ | Value |
| Currency | ✅ | |
| ReportDate | ✅ | |
| TransactionID | ✅ | |

### ✅ Section 4: Option Exercises, Assignments & Expirations

Very important! This section is separate from Trades and contains the special option cases.

| Field | Do we need it? | Why |
| :--- | :---: | :--- |
| DateTime | ✅ | Time |
| Symbol | ✅ | Option symbol |
| UnderlyingSymbol | ✅ | Underlying stock |
| Strike | ✅ | |
| Expiry | ✅ | |
| Put/Call | ✅ | |
| Quantity | ✅ | |
| TradePrice | ✅ | |
| ActionType | ✅ | Assignment, Exercise, Expiration, Lapse |
| Description | ✅ | |
| Currency | ✅ | |
| Multiplier | ✅ | |
| FXRateToBase | ✅ | |

### ☑️ Section 5: Open Positions (Optional, for Verification)

| Field | Do we need it? | Why |
| :--- | :---: | :--- |
| Symbol | ✅ | |
| Quantity | ✅ | Comparison with our FIFO result |
| CostBasisPrice | ✅ | IBKR's calculation for comparison |
| CostBasisMoney | ✅ | |
| AssetCategory | ✅ | |
| Currency | ✅ | |
| FifoPnlUnrealized | ☑️ | For comparison |
| MarkPrice | ☑️ | Current price |

### ☑️ Section 6: Interest Accruals (Optional)
For accrued interest on bonds. Only necessary if you trade bonds.

### ❌ Sections We Do NOT Need

| Section | Why not |
| :--- | :--- |
| Account Information | Extractable once from the header |
| Change in NAV | Performance report, not tax-relevant |
| Financial Instrument Information | Nice, but not necessary |
| Net Stock Position Summary | Summary, we calculate ourselves |
| Prior Period Adjustment | Only for corrections |
| SLB Activities | Securities Lending, only relevant for lenders |
| Statement of Funds | Cash flow, not tax-relevant |
| Trade Confirmations | Duplicate of Trades |
| Transfers | Deposits/Withdrawals, not tax-relevant |
| Unbooking | Not relevant |

## 4. Summary: Your Flex Query Configuration

| Configuration | Value |
| :--- | :--- |
| **Name** | `IBKR2KAP_Full_Export` |
| **Format** | `XML` |
| **Period** | `Last 365 Calendar Days` |
| **✅ Trades** | (all fields as above) |
| **✅ Cash Transactions** | (Dividends, Interest) |
| **✅ Corporate Actions** | (Splits, Mergers) |
| **✅ Option Exercises** | (Expiration, Exercise, Assignment) |
| **☑️ Open Positions** | (for verification) |
| **❌ Everything else** | (not needed) |

## 5. Recommended Export Strategy

Because of IBKR's 365-day limit on Flex Queries, you must piece together your history so the FIFO engine can accurately reconstruct your cost basis from the very beginning.

┌─────────────────────────────────────────────────────────────┐
│  RECOMMENDED DATA EXPORT PROCEDURE                          │
│                                                             │
│  1. Create ONE Flex Query "IBKR2KAP_Full_Export"            │
│     with Period = "Last 365 Calendar Days"                  │
│     and ALL Sections as described above.                    │
│                                                             │
│  2. Run the query MULTIPLE TIMES:                           │
│     - Run it once now (covers 2024/present)                 │
│     - Change the Period to "Last Calendar Year"             │
│       and run it again (for 2023)                           │
│     - Repeat for 2022, 2021, etc., back to account opening. │
│                                                             │
│  3. OR: Export an Activity Statement CSV                    │
│     with Custom Date Range (Account opening to today)       │
│                                                             │
│  4. Upload ALL exported files into ibkr2kap                 │
│     → Duplicates are automatically detected.                │
│     → FIFO is correctly built across all data.              │
└─────────────────────────────────────────────────────────────┘
