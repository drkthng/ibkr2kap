---
phase: 28
plan: 1
wave: 1
---

# Plan 28.1: ManualPosition Backend Model & FIFO Integration

## Objective
Create the `ManualPosition` database model, integrate it into the `FIFORunner` as a new event type (like `transfer`), and add a `manual_position_id` FK to `FIFOLot`. This enables users to provide cost basis for positions acquired before XML data coverage.

## Context
- .gsd/SPEC.md
- .gsd/phases/28/RESEARCH.md
- src/ibkr_tax/models/database.py
- src/ibkr_tax/services/fifo_runner.py
- src/ibkr_tax/services/transfer_engine.py (pattern to follow)
- src/ibkr_tax/services/maintenance.py
- src/ibkr_tax/db/repository.py
- tests/conftest.py

## Tasks

<task type="auto">
  <name>Add ManualPosition model to database.py</name>
  <files>src/ibkr_tax/models/database.py</files>
  <action>
    Add a new `ManualPosition` class to `database.py`:
    ```python
    class ManualPosition(Base):
        __tablename__ = "manual_positions"
        id: Mapped[int] = mapped_column(primary_key=True)
        account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
        symbol: Mapped[str] = mapped_column(index=True)
        asset_category: Mapped[str] = mapped_column()  # STK, OPT, etc.
        quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4))
        acquisition_date: Mapped[str] = mapped_column()  # ISO date YYYY-MM-DD (Settlement)
        cost_basis_total_eur: Mapped[Decimal] = mapped_column(Numeric(18, 4))
        description: Mapped[str] = mapped_column(default="Manual Opening Position")

        account: Mapped["Account"] = relationship(back_populates="manual_positions")
    ```
    
    Also update:
    1. `Account` model: add `manual_positions: Mapped[List["ManualPosition"]] = relationship(back_populates="account")`
    2. `FIFOLot` model: add `manual_position_id: Mapped[int | None] = mapped_column(ForeignKey("manual_positions.id"), nullable=True)` and `manual_position: Mapped["ManualPosition"] = relationship()`
  </action>
  <verify>
    Run `python -c "from ibkr_tax.models.database import ManualPosition, FIFOLot; print('OK')"` from the project root.
  </verify>
  <done>ManualPosition model exists with all fields. FIFOLot has manual_position_id FK. Account has manual_positions relationship.</done>
</task>

<task type="auto">
  <name>Integrate ManualPosition into FIFORunner & cleanup</name>
  <files>src/ibkr_tax/services/fifo_runner.py, src/ibkr_tax/services/maintenance.py</files>
  <action>
    **FIFORunner (`fifo_runner.py`):**
    1. Import `ManualPosition` from `database.py`.
    2. In `run_for_account`, after fetching transfers (step 4), add step 5: fetch all ManualPosition records for the account:
       ```python
       stmt_manual = (
           select(ManualPosition)
           .where(ManualPosition.account_id == account_id)
       )
       manual_positions = self.session.execute(stmt_manual).scalars().all()
       ```
    3. Add manual positions to the events list with type `"manual"` and date from `acquisition_date`. Priority should be -1 (before transfers, before actions, before trades) on the same date:
       ```python
       for mp in manual_positions:
           events.append({"date": mp.acquisition_date, "type": "manual", "obj": mp, "id": mp.id})
       ```
    4. Update the sort key to include manual type with priority -1:
       ```python
       type_priority = {"manual": -1, "transfer": 0, "action": 1, "trade": 2}
       events.sort(key=lambda x: (x["date"], type_priority.get(x["type"], 99), x["id"]))
       ```
    5. Add processing logic in the event loop:
       ```python
       elif event["type"] == "manual":
           self._process_manual_position(event["obj"])
       ```
    6. Add `_process_manual_position` method that creates a `FIFOLot`:
       ```python
       def _process_manual_position(self, mp: ManualPosition):
           quantity = mp.quantity
           cost_basis = mp.cost_basis_total_eur
           if quantity == 0:
               return
           lot = FIFOLot(
               trade_id=None,
               corporate_action_id=None,
               transfer_id=None,
               manual_position_id=mp.id,
               asset_category=mp.asset_category,
               symbol=mp.symbol,
               settle_date=mp.acquisition_date,
               original_quantity=quantity,
               remaining_quantity=quantity,
               cost_basis_total=cost_basis,
               cost_basis_per_share=cost_basis / abs(quantity),
           )
           self.session.add(lot)
           self.session.flush()
       ```
    7. In `_clear_fifo_data`, add cleanup for manual position lots:
       ```python
       mp_ids_stmt = select(ManualPosition.id).where(ManualPosition.account_id == account_id)
       mp_ids = self.session.execute(mp_ids_stmt).scalars().all()
       if mp_ids:
           self.session.execute(
               delete(FIFOLot).where(FIFOLot.manual_position_id.in_(mp_ids))
           )
       ```

    **Maintenance (`maintenance.py`):**
    1. Import `ManualPosition` and `Transfer`.
    2. Add `ManualPosition` and `Transfer` to the `models_to_clear` list (ManualPosition before Trade/CashTransaction, Transfer before Trade).
  </action>
  <verify>
    `python -c "from ibkr_tax.services.fifo_runner import FIFORunner; print('OK')"`
  </verify>
  <done>FIFORunner processes ManualPosition events as FIFOLots. _clear_fifo_data handles manual lots. MaintenanceService clears manual positions on reset.</done>
</task>

<task type="auto">
  <name>Write unit tests for ManualPosition + FIFO integration</name>
  <files>tests/test_manual_positions.py</files>
  <action>
    Create `tests/test_manual_positions.py` with the following tests using the `db_session` fixture from `conftest.py`:

    1. **test_manual_position_creates_fifo_lot**: Create Account, ManualPosition (100 AAPL, 2020-01-03, 10000€), run FIFORunner → verify 1 FIFOLot with correct quantity, cost_basis, settle_date, and manual_position_id set.
    
    2. **test_manual_position_resolves_sell**: Create Account, ManualPosition (100 AAPL, 2020-01-03, 10000€), then Trade SELL 50 AAPL (2023-02-03, proceeds 8000€, fx 1.0). Run FIFORunner → verify 1 Gain with correct realized_pnl = 8000 - 5000 = 3000 (minus commission). FIFOLot remaining = 50.
    
    3. **test_manual_position_idempotency**: Run FIFORunner twice for same account with a ManualPosition → verify only 1 FIFOLot exists (not duplicated).
    
    4. **test_manual_position_interleaving_order**: Create ManualPosition (date 2020-01-01), Trade BUY (2021-01-03), Trade SELL (2023-01-03). Run FIFORunner → verify FIFO matches against the manual position first (oldest).
    
    5. **test_maintenance_clears_manual_positions**: Create ManualPosition, run MaintenanceService.reset_database() → verify manual_positions table is empty.
  </action>
  <verify>
    `uv run pytest tests/test_manual_positions.py -v`
  </verify>
  <done>All 5 tests pass. ManualPosition model, FIFO integration, and maintenance cleanup are all verified.</done>
</task>

## Success Criteria
- [ ] `ManualPosition` model exists in `database.py` with all required fields
- [ ] `FIFOLot` has `manual_position_id` FK
- [ ] `FIFORunner` creates `FIFOLot` from `ManualPosition` with correct date ordering
- [ ] `_clear_fifo_data` handles manual position lots
- [ ] `MaintenanceService.reset_database()` clears `manual_positions` table
- [ ] All 5 unit tests pass
- [ ] Full regression suite passes (`uv run pytest`)
