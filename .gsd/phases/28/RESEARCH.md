# Research: Phase 28 — Manual Cost-Basis Entry UI

## Problem Statement
IBKR Flex Query XML files often only cover a specific period. If a user sells a security they bought *before* the start of the XML data, the system flags it as "Missing Cost Basis" (negative `FIFOLot`). To calculate correct German tax gains, the user needs to provide the acquisition date and cost basis for these "opening" positions.

## Proposed Solution: `ManualPosition` Model

We will introduce a new table to store user-provided opening positions. These will be treated by the `FIFORunner` as "acquisition events" similar to trades or transfers.

### 1. Database Model
```python
class ManualPosition(Base):
    __tablename__ = "manual_positions"
    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    symbol: Mapped[str] = mapped_column(index=True)
    asset_category: Mapped[str] = mapped_column() # STK, OPT, etc.
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    acquisition_date: Mapped[str] = mapped_column() # ISO (Settle Date equivalent)
    cost_basis_total_eur: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    description: Mapped[str] = mapped_column(default="Manual Opening Position")
    
    account: Mapped["Account"] = relationship(back_populates="manual_positions")
```

### 2. Integration with `FIFORunner`
The `FIFORunner.run_for_account` method will be updated to:
1. Fetch all `ManualPosition` records for the account.
2. Interleave them into the event list as `type="manual"`.
3. Process them by calling a new `FIFOEngine.process_manual_position` method (or similar) that adds them to the inventory.

### 3. Integration with `FIFOLot`
Update `FIFOLot` to include `manual_position_id`:
```python
manual_position_id: Mapped[int | None] = mapped_column(ForeignKey("manual_positions.id"), nullable=True)
manual_position: Mapped["ManualPosition"] = relationship()
```

### 4. UI Design
- **New Tab / Section**: "Manual Data Entry".
- **Functionality**:
    - List existing manual positions (with "Delete" option).
    - Form to add a new manual position:
        - Account (Dropdown)
        - Symbol (Text)
        - Asset Category (Dropdown: STK, OPT, etc.)
        - Acquisition Date (Date Picker) -> converted to ISO string.
        - Quantity (Number)
        - Cost Basis in EUR (Number)
        - Description (Optional Text)

### 5. Why not use the `Trade` table?
- `Trade` expects an `ib_trade_id` from IBKR, which is unique. Manual entries don't have one.
- `Trade` has fields like `proceeds`, `commission`, `taxes`, `fx_rate_to_base` which are redundant for a manual "Opening Balance" entry where the user likely just knows the final EUR cost.
- Keeping manual entries separate prevents accidental deletion/corruption during XML imports.

## Alternatives Considered
- **Pseudo-Transfers**: Using the existing `Transfer` table.
    - Cons: `Transfer` is complex and has specific direction/counterparty logic. "Opening Balance" is not really a transfer from another account (in the current system's context).
- **Direct `FIFOLot` Insertion**: Manually adding lots.
    - Cons: `FIFORunner` wipes `FIFOLot` table on every run. Manual entries must exist in a source table to survive a re-run.
