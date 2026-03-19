# IBKR2KAP Roadmap

## Milestone v1.0: Core Ingestion & Basic FIFO (Complete)
- [x] Phase 0: System Architecture & Database Schema
- [x] Phase 1: IBKR Flex Query XML Parser (Trades & Cash)
- [x] Phase 2: Fundamental Repository Patterns
- [x] Phase 3: Interactive CLI for Data Import
- [x] Phase 4: Core FIFO Matching Logic (Stocks)
- [x] Phase 5: FIFO Idempotency & Persistence
- [x] Phase 6: Basic PnL Reporting (CLI)

## Milestone v1.1: German Tax Logic & Enhanced UX (Complete)
- [x] Phase 7: Corporate Action Engine (Stock Splits)
- [x] Phase 8: German Tax Categorization (Aktien vs. Sonstige)
- [x] Phase 9: FX Conversion Engine (ECB Rates Integration)
- [x] Phase 10: Streamlit UI Implementation (Web Interface)
- [x] Phase 11: Excel Export Service (Tax Consultant Format)
- [x] Phase 12: Bi-directional FIFO & Option Logic (Exercise/Assignment)
- [x] Phase 13: End-to-End Integration Testing
- [x] Phase 14: Windows & macOS App Launchers
- [x] Phase 15: XML Ingestion Deep Inspection (Unmapped Entities)
- [x] Phase 16: UI Refinement & Database Browser
- [x] Phase 17: Dynamic UI Components (Account/Year selection)
- [x] Phase 18: Buy-Date Reporting for Gains/Losses
- [x] Phase 19: Missing Cost-Basis Reporting & Prompts
- [x] Phase 20: App Launch Options & Documentation
- [x] Phase 21: Bug Fix: Missing Cost-Basis Reporting
- [x] Phase 22: UI and FX Bug Fixes
- [x] Phase 23: Descriptive Warnings and Database Maintenance

## Milestone v1.2: Advanced Corporate Actions & Compliance
- [x] Phase 24: Core Spinoff Support & FIFO Integration
- [x] Phase 25: Reverse Split with Symbol/ISIN Rename (Consolidation)
- [x] Phase 26: German Tax Theory Document & UI Guidance
- [x] Phase 27: Inter-Account Transfer Support (FIFO Lot Migration)
- [x] Phase 28: Manual Cost-Basis Entry UI (Missing Open Positions)
- [x] Phase 29: FX Engine Redesign (Anlage SO)
- [x] Phase 30: UX Improvements (Selectability, Prefill, Multi-file Import)
- [x] Phase 31: Advanced Manual Entry Fields (Full trade detail support + manual closing trades)
- [x] Phase 33: Tax Compliance (Margin Interest & Deductions)
- [x] Phase 34: Report & UI Refinement

---

### Phase 35: Multi-Account Combined Reporting
**Status**: ⬜ Not Started
**Objective**: Ability to create a combined report for multiple accounts while still showing individual account summaries. Include account origin in detail tabs.
**Depends on**: Phase 34

**Tasks**:
- [ ] TBD (run /plan 35 to create)

**Verification**:
- TBD

---

### Phase 36: Report Output Remodel (Tax-Law Compliant)
- **Status**: [COMPLETED] 2026-03-19
- **Objective**: Remodel report outputs to respect the German "Zwei-Töpfe" principle (§ 20 Abs. 6 EStG).
- **Dependencies**: Phase 33, Phase 35
- **Tasks**:
  - [x] Update `TaxReport` schema to include `aktien_net_result` and `allgemeiner_topf_result`.
  - [x] Modify `TaxAggregatorService` to compute separated tax pools.
  - [x] Remodel Excel summary sheet for tax-pool clarity.
  - [x] Update Streamlit UI to display separate pool metrics.
  - [x] Verify with unit and integration tests.

## Future Milestone: v2.0 (Planned)
- [ ] Support for multiple broker imports (Trade Republic, Scalable Capital).
- [ ] Real-time crypto portfolio tracking & FIFO matching.
