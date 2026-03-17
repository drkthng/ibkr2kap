---
phase: 27
plan: 2
wave: 2
---

# Plan 27.2: FIFO Lot Migration Engine & Tests

## Objective
Implement the core tax-critical logic: when a stock position is transferred between accounts (direction=IN), create new FIFO lots in the receiving account that preserve the original cost basis from the sending account. This ensures the tax-neutral nature of internal transfers is correctly reflected in FIFO matching.

**German Tax Law:** An internal transfer between an investor's own IBKR sub-accounts is NOT a taxable event. The cost basis (Anschaffungskosten) carries over 1:1 into the new account. When the position is eventually sold in the receiving account, the original acquisition date and cost basis must be used for FIFO matching.

## Context
- .gsd/phases/27/1-PLAN.md (must be completed first)
- src/ibkr_tax/models/database.py (Transfer model, FIFOLot with transfer_id FK)
- src/ibkr_tax/services/fifo.py (existing FIFOEngine._add_to_inventory pattern)
- src/ibkr_tax/services/fifo_runner.py (orchestrator for FIFO processing)
- src/ibkr_tax/services/pipeline.py (integration point)
- example/U7330779_U7230673_IBKR2KAP_Full_Export_2022.xml (AEHR transfer: 22 shares in, positionAmount=527.164)
- example/U7330779_U7230673_IBKR2KAP_Full_Export_2024.xml (MGNT/SIBN/SNGSP transfers out)

## Tasks

<task type="auto">
  <name>Implement TransferEngine for FIFO lot migration</name>
  <files>
    src/ibkr_tax/services/transfer_engine.py [NEW]
    src/ibkr_tax/services/pipeline.py
  </files>
  <action>
    Create `src/ibkr_tax/services/transfer_engine.py`:
    - Class `TransferEngine(session: Session)`:
      - `process_transfers()`: Query all Transfer records from DB, process IN-direction stock transfers
      - For each stock transfer with direction="IN" and quantity > 0:
        - Create a FIFOLot with:
          - `transfer_id` = Transfer.id (new FK)
          - `trade_id` = None (not from a trade)
          - `corporate_action_id` = None
          - `symbol` = Transfer.symbol
          - `asset_category` = "STK" (transfers are stock-only in IBKR)
          - `settle_date` = Transfer.settle_date
          - `original_quantity` = Transfer.quantity
          - `remaining_quantity` = Transfer.quantity
          - `cost_basis_total` = Transfer.position_amount_in_base (already in EUR)
          - `cost_basis_per_share` = cost_basis_total / quantity
        - Skip if a FIFOLot with this transfer_id already exists (idempotency)
      - For direction="OUT" transfers: do NOT create negative lots.
        The FIFO engine handles sell-side matching naturally. The OUT record
        is informational — the shares leave via being consumed by FIFO matching.
      - For cash-only transfers (quantity=0): skip entirely — no FIFO impact.
      - Return count of lots created.

    Update `pipeline.py`:
    - After import_transfers() and before fifo_runner.run_all():
      - Instantiate TransferEngine and call process_transfers()
      - This ensures transferred lots exist BEFORE FIFO sell matching runs.
  </action>
  <verify>python -c "from ibkr_tax.services.transfer_engine import TransferEngine; print('OK')"</verify>
  <done>
    - TransferEngine creates FIFOLots for IN-direction stock transfers
    - Lots have correct cost basis from positionAmountInBase
    - Pipeline integrates transfer processing before FIFO matching
    - Cash-only and OUT transfers are correctly skipped
  </done>
</task>

<task type="auto">
  <name>Write comprehensive tests for transfer parsing and FIFO migration</name>
  <files>
    tests/test_transfer_engine.py [NEW]
    tests/test_flex_parser.py (add transfer parsing tests)
  </files>
  <action>
    Create `tests/test_transfer_engine.py`:
    - Test: stock transfer IN creates FIFOLot with correct cost basis
    - Test: stock transfer OUT does NOT create a FIFOLot
    - Test: cash-only transfer (qty=0, symbol="--") does NOT create a FIFOLot
    - Test: idempotency — processing same transfers twice creates lots only once
    - Test: transferred lot participates in FIFO matching when shares are sold

    Add to `tests/test_flex_parser.py` (or new file `tests/test_flex_parser_transfers.py`):
    - Test: get_transfers() parses stock transfer with all fields
    - Test: get_transfers() parses cash-only transfer
    - Test: Transfers removed from unmapped entities after parser update

    Use real XML snippets from the example files for test data.
    Use the existing `conftest.py` fixtures for sessions (check if exists).
  </action>
  <verify>python -m pytest tests/test_transfer_engine.py -x -v</verify>
  <done>
    - All transfer-related tests pass
    - Coverage: parsing, stock IN/OUT, cash-only, idempotency, FIFO integration
    - Full regression suite still passes (python -m pytest tests/ -x)
  </done>
</task>

## Success Criteria
- [ ] `TransferEngine.process_transfers()` creates correct FIFOLots for IN transfers
- [ ] Cost basis is preserved from `positionAmountInBase` (EUR value)
- [ ] Cash-only and OUT transfers create no lots
- [ ] Processing is idempotent
- [ ] Transferred lots participate correctly in subsequent FIFO sell matching
- [ ] Full test suite passes with no regressions
- [ ] E2E test with real 2022 XML produces AEHR FIFOLot with correct cost basis
