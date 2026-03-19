---
phase: 34
plan: 2
wave: 2
---
# 34-2: Excel Export Enhancements

## Goals
1. Separate Deposits & Withdrawals in Excel Export into a new tab.
2. Add mathematical explanation to the Summary tab for Total Realized PnL.

## Tasks
1. [ ] Implement `_add_deposits_withdrawals_sheet()` in `ExcelExportService.py`.
2. [ ] Filter `Deposits & Withdrawals` out from Dividends sheet.
3. [ ] Add formula breakdown rows to the `Summary` tab.
4. [ ] Verify Excel export by generating a report for the user's data.
