# IBKR Flex Query Setup

To use the IBKR2KAP tax tool, you need to generate an **Activity Flex Query** in Interactive Brokers. The query must contain specific sections and fields so our system can construct a compliant German tax report using the FIFO method.

Follow these step-by-step instructions.

## 1. Navigation to the Flex Query Builder

1. **Login:** [Interactive Brokers Portal](https://portal.interactivebrokers.com)
2. **Menu:** Performance & Reports → Flex Queries
3. Click the **[+]** button under **"Activity Flex Queries"**.
   > *Note: Do NOT choose "Trade Confirmation Flex Query" – this is something else.*

## 2. Basic Settings

┌─────────────────────────────────────────────────────────────┐
│  Query Name:        IBKR2KAP_Full_Export                    │
│                                                             │
│  Date Period:       Custom Date Range                       │
│  From:              (Account opening date, e.g., 2020-01-01)│
│  To:                2024-12-31                              │
│                                                             │
│  Format:            XML                                     │
│  Delivery:          Online (Download)                       │
│  Period:            (leave blank)                           │
│                                                             │
│  Include canceled trades:  ☐ No                             │
│  Include audit trail:      ☐ No                             │
│  Include Cost Basis in Pos: ☑ Yes                           │
└─────────────────────────────────────────────────────────────┘

> **IMPORTANT:** The "From" date must be the day you opened your account (or the first day you traded). Only then can the FIFO cost-basis be properly reconstructed for all open positions!

## 3. Sections and Fields – Exactly What You Need

In the Flex Query Builder, you will see a list of sections. For each section, select the fields below.

### ✅ Section 1: Trades (CRITICAL)

Click on **"Trades"** and select the following:

**Identification:**
- `TradeID` ✅ (Unique ID, deduplication)
- `IBOrderID` ✅ (Matching related trades)
- `IBExecID` ☑️ (Helpful for debugging)

**Instrument:**
- `Symbol` ✅
- `Description` ✅
- `AssetCategory` ✅ (STK, OPT, FUT, CASH – for tax pool assignment)
- `ISIN` ✅ (Required by tax consultants)
- `UnderlyingSymbol` ✅ (For options: underlying stock)
- `Multiplier` ✅ (For options: usually 100)
- `Strike` ✅ (For options)
- `Expiry` ✅ (For options)
- `Put/Call` ✅ (P or C)
- `SecurityID` ☑️
- `SecurityIDType` ☑️ (e.g., "ISIN")
- `ConID` ☑️ (IBKR Contract ID)

**Trade Details:**
- `DateTime` ✅ 
- `TradeDate` ✅ 
- `SettleDateTarget` ✅ (**CRITICAL!** Determines the tax year!)
- `Buy/Sell` ✅
- `Quantity` ✅
- `TradePrice` ✅
- `Proceeds` ✅
- `IBCommission` ✅
- `IBCommissionCurrency` ✅
- `NetCash` ✅
- `Currency` ✅
- `FXRateToBase` ✅ (For comparison; we use ECB rates)
- `OpenCloseIndicator` ✅ (O=Opening, C=Closing; crucial for options!)
- `Notes/Codes` ✅ (**CRITICAL!** Contains "A", "Ex", "Ep")
- `CostBasis` ☑️ 
- `RealizedPnL` ☑️ 
- `TransactionType` ✅
- `LevelOfDetail` ✅ (Set to "EXECUTION")

---

### ✅ Section 2: Cash Transactions (DIVIDENDS + INTEREST)

*(Note: Depending on your IBKR portal version, these may be separate "Dividends" and "Interest" sections, but usually combined in XML).*

- `DateTime` ✅ 
- `Symbol` ✅ 
- `ISIN` ✅
- `Description` ✅ (Details like "Cash Dividend...")
- `Amount` ✅
- `Currency` ✅
- `Type` ✅ (**CRITICAL!** Dividends, Payment In Lieu Of Dividends, Bond Interest, etc.)
- `FXRateToBase` ✅ 
- `ReportDate` ✅ (For tax year)
- `SettleDate` ✅ (For tax year)
- `ActionID` ☑️ (For mapping to withholding tax)

> **Watch out:** "Payment in Lieu of Dividends" are substitute payments (when your shares were lent out) and face different tax logic!

---

*(Section 3 - Withholding Tax has been temporarily excluded as it cannot be set up completely standalone in some configurations).*

---

### ✅ Section 4: Corporate Actions

- `DateTime` ✅
- `Symbol` ✅
- `ISIN` ✅
- `Description` ✅ (**CRITICAL!** Contains Split-Ratio, Merger details)
- `ActionType` ✅ (SO, TC, FS, etc.)
- `Quantity` ✅
- `Value` ✅
- `Currency` ✅
- `ReportDate` ✅
- `TransactionID` ✅

---

### ✅ Section 5: Option Exercises, Assignments & Expirations

*(Crucial for mapping option paths!)*

- `DateTime` ✅
- `Symbol` ✅
- `UnderlyingSymbol` ✅
- `Strike` ✅
- `Expiry` ✅
- `Put/Call` ✅
- `Quantity` ✅
- `TradePrice` ✅
- `ActionType` ✅ (Assignment, Exercise, Expiration, Lapse)
- `Description` ✅
- `Currency` ✅
- `Multiplier` ✅
- `FXRateToBase` ✅

---

### ☑️ Section 6: Open Positions (Optional, for Verification)

Useful if you want to verify our FIFO output against IBKR’s internal calculations.

- `Symbol` ✅
- `Quantity` ✅
- `CostBasisPrice` ✅
- `CostBasisMoney` ✅
- `AssetCategory` ✅
- `Currency` ✅

---

### ❌ Sections We Do NOT Need
Do not include these, as they bloat the XML file:
- Account Information, Change in NAV, Financial Instrument Info, Net Stock Position Summary, Prior Period Adjustment, SLB Activities, Statement of Funds, Trade Confirmations, Transfers.

## 4. Summary

┌─────────────────────────────────────────────────────────────┐
│  FLEX QUERY CONFIGURATION FOR ibkr2kap                      │
│                                                             │
│  Name:    IBKR2KAP_Full_Export                              │
│  Format:  XML                                               │
│  Period:  Account Opening Date to 31.12.2024                │
│                                                             │
│  ✅ Trades              (all fields above)                  │
│  ✅ Cash Transactions   (Dividends, Interest)               │
│  ✅ Corporate Actions   (Splits, Mergers)                   │
│  ✅ Option Exercises    (Expiration, Exercise, Assignment)  │
│  ☑️ Open Positions      (for verification)                  │
│  ❌ Everything else     (not needed)                        │
└─────────────────────────────────────────────────────────────┘
