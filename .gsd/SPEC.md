# SPEC.md — Project Specification

> **Status**: `FINALIZED`

## Vision
A robust, local-first application for German retail investors who use Interactive Brokers. It automatically imports trade data (via Flex Query XML or CSV), calculates FIFO-based capital gains and losses with exact ECB exchange rates, categorizes everything according to current German tax laws, and exports an Excel report ready for the tax consultant ("Anlage KAP").

## Goals
1. Accurately parse IBKR Flex Query XML (and CSV as a fallback).
2. Calculate FIFO gains/losses precisely using `decimal` types and official ECB exchange rates (including weekend fallbacks).
3. Correctly categorize capital gains according to German tax law (Aktienverrechnungstopf, Termingeschäfte without the 20k limit due to JStG 2024, Dividends, Withholding Taxes).
4. Handle option expiries, exercises, and assignments correctly (no separate gain/loss for exercises/assignments, premiums adjust the stock cost basis).
5. Generate an Excel report that tax consultants can directly map to "Anlage KAP" lines (7, 8, 9, 10, 15).
6. Provide a simple, fast local UI using Streamlit.

## Non-Goals (Out of Scope)
- No cloud hosting, no multi-user SaaS system.
- No real-time trading, charting, or portfolio management.
- Complex Merger/Spinoff corporate actions (deferred to a later phase or ignored).

## Users
German retail investors and traders utilizing Interactive Brokers, and their tax consultants who need clean, rule-compliant, and verifiable tax reports.

## Constraints
- **Tech Stack:** Python 3.12+, SQLAlchemy 2.0 (SQLite), Pydantic v2, Streamlit, and `pytest` for TDD.
- **Data Precision:** Strict usage of `decimal.Decimal` or `Numeric` for all monetary amounts; NEVER use floats.
- **Legal Compliance:** Must follow German tax laws strictly: FIFO valuation, separation of stock and option loss pools, processing transactions based on the settlement date (Settle-Date) for tax year assignment.
