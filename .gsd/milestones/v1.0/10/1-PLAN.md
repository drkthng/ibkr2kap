---
phase: 10
plan: 1
wave: 1
---

# Plan 10.1: Corporate Actions Engine — Stock Splits

## Objective
Implement a `CorporateActionEngine` service and a `CorporateActionSchema` Pydantic schema to handle stock splits. A stock split modifies open `FIFOLot` records by multiplying `remaining_quantity` and `original_quantity` by the split ratio while dividing `cost_basis_per_share` by the same ratio — keeping `cost_basis_total` unchanged. This follows the established `OptionEngine` pattern.

## Context
- .gsd/SPEC.md
- .gsd/ROADMAP.md
- src/ibkr_tax/models/database.py
- src/ibkr_tax/services/option_engine.py (pattern reference)
- src/ibkr_tax/schemas/ibkr.py

## Tasks

<task type="auto">
  <name>Create CorporateActionSchema</name>
  <files>src/ibkr_tax/schemas/ibkr.py</files>
  <action>
    Add a new `CorporateActionSchema` class to `src/ibkr_tax/schemas/ibkr.py`:
    
    Fields:
    - `account_id: str` (required, min_length=1)
    - `symbol: str` (required, min_length=1) — the stock symbol (e.g., "AAPL")
    - `action_type: Literal["StockSplit", "ReverseStockSplit"]`
    - `date: date` — effective date of the corporate action
    - `ratio: Decimal` — the split ratio (e.g., `Decimal("4")` for 4:1 forward split, `Decimal("0.1")` for 1:10 reverse split)
    - `description: str` — human-readable description from IBKR

    Inherit from `BaseIBKRSchema` to get the float-rejection validator.

    Add a model_validator to ensure `ratio > 0`.

    AVOID: Adding any database model yet — we don't persist corporate actions, we just apply them as mutations to FIFOLots.
  </action>
  <verify>python -c "from ibkr_tax.schemas.ibkr import CorporateActionSchema; print('OK')"</verify>
  <done>CorporateActionSchema importable and validates a sample input without errors</done>
</task>

<task type="auto">
  <name>Create CorporateActionEngine service</name>
  <files>src/ibkr_tax/services/corporate_actions.py</files>
  <action>
    Create a new file `src/ibkr_tax/services/corporate_actions.py` with class `CorporateActionEngine`:

    ```python
    class CorporateActionEngine:
        def __init__(self, session: Session):
            self.session = session

        def apply_stock_split(self, action: CorporateActionSchema):
            """Applies a stock split to all open FIFOLots for the given symbol."""
            # 1. Query all FIFOLots where symbol == action.symbol AND remaining_quantity != 0
            # 2. For each lot:
            #    - lot.original_quantity *= action.ratio
            #    - lot.remaining_quantity *= action.ratio
            #    - lot.cost_basis_per_share /= action.ratio (recalculated)
            #    - lot.cost_basis_total stays UNCHANGED (this is the key tax rule)
            # 3. session.flush()
    ```

    Key rules:
    - Only modify lots that have `remaining_quantity != 0` (open lots)
    - A forward 4:1 split has ratio=4: qty × 4, cost/share ÷ 4
    - A reverse 1:10 split has ratio=0.1: qty × 0.1, cost/share ÷ 0.1
    - cost_basis_total must NEVER change (German tax law: Anschaffungskosten bleiben gleich)
    - Use Decimal arithmetic only, no floats

    Follow the same class pattern as OptionEngine (constructor takes session, methods query FIFOLots).
  </action>
  <verify>python -c "from ibkr_tax.services.corporate_actions import CorporateActionEngine; print('OK')"</verify>
  <done>CorporateActionEngine importable and contains apply_stock_split method</done>
</task>

## Success Criteria
- [ ] `CorporateActionSchema` validates correctly with float rejection
- [ ] `CorporateActionEngine.apply_stock_split` modifies lots correctly
- [ ] No database model changes needed (pure lot mutation)
- [ ] Pattern mirrors OptionEngine (session-based, query-then-mutate)
