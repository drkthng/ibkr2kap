# ROADMAP.md

> **Current Phase**: Phase 6 complete
> **Milestone**: v1.0

## Must-Haves (from SPEC)
- [ ] Python 3.12 Environment setup with Database.
- [ ] Parse Flex Query XML correctly.
- [x] Validated data correctly persistent in SQLite.
- [ ] Tax compliant FIFO engine for accurately matching lots based on settlement dates.
- [ ] Tax categorization engine for mapping to "Anlage KAP".
- [ ] Tax Consultant Excel Report Export.
- [ ] Local Streamlit UI for the end-user.

## Phases

### Phase 0: Project Setup
**Status**: ✅ Complete
**Objective**: Basic project scaffolding, Poetry/uv configuration, SQLite + SQLAlchemy setup, and a "Hello World" test.

### Phase 1: Database Models
**Status**: ✅ Complete
**Objective**: Map strict SQLAlchemy 2.0 ORM models (Account, Trade, CashTransaction, FIFOLot, Gain) representing the full IBKR data structure and tax matching logic.

### Phase 2: Pydantic Validation Schemas
**Status**: ✅ Complete
**Objective**: Build strict, typed data validation for raw IBKR inputs before database insertion.

### Phase 3: ECB Exchange Rates
**Status**: ✅ Complete
**Objective**: Exchange calculation engine referencing official ECB rates with weekend fallback (cacheable in DB).

### Phase 4: IBKR Flex Query XML Parser
**Status**: ✅ Complete
**Objective**: Ingest the reliable XML structure using `ibflex` and map the raw structures to our Pydantic validation schemas.

### Phase 5: IBKR CSV Activity Statement Parser (Fallback)
**Status**: ✅ Complete
**Objective**: Fallback parser handling IBKR's specific Section/Header/Data CSV formats.

### Phase 6: Data Import Pipeline
**Status**: ✅ Complete
**Objective**: Write validated external data correctly to the SQLite database via repository patterns, ensuring idempotency and duplication prevention.

### Phase 7: FIFO Engine
**Status**: ✅ Complete

### Phase 8: Tax Categorization
**Status**: ⬜ Not Started
**Objective**: Allocate realized gains to German tax pools (Aktienverlusttopf vs. Allgemeiner Topf) mapping cleanly to Anlage KAP columns.

### Phase 9: Options Edge Cases
**Status**: ⬜ Not Started
**Objective**: Handle complex but crucial mechanisms around options: expirations, assignments, and exercises modifying stock basic costs.

### Phase 10: Corporate Actions
**Status**: ⬜ Not Started
**Objective**: Handle standard Stock Splits (changing quantities but maintaining cost basis).

### Phase 11: Excel Export
**Status**: ⬜ Not Started
**Objective**: Use `openpyxl` to produce elegantly formatted reports designed specifically for tax consultants.

### Phase 12: Streamlit UI
**Status**: ⬜ Not Started
**Objective**: Frontend experience providing data import capabilities, execution of tax routines, and viewing of individual lot deductions.

### Phase 13: End-to-End Integration
**Status**: ⬜ Not Started
**Objective**: Connect all units with an overarching realistic, multi-year e2e test scenario evaluating full correctness.

### Phase 14: Currency Gains (Optional)
**Status**: ⬜ Not Started
**Objective**: (Extremely Complex) Address §23 EStG on foreign currency holdings matching. Marked as highly optional.
