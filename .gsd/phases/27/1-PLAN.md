---
phase: 27
plan: 1
wave: 1
---

# Plan 27.1: Transfer Schema, Parser & Database Model

## Objective
Add the foundational data layer for inter-account transfers: Pydantic schema, database model, repository import, and XML parser extraction. This enables the system to ingest `<Transfers>` data from IBKR Flex Query XML files.

**German Tax Context:** Inter-account transfers (INTERNAL type) are tax-neutral events — they migrate FIFO lots between accounts while preserving cost basis. Cash transfers are informational only (no tax impact).

## Context
- .gsd/SPEC.md
- src/ibkr_tax/schemas/ibkr.py (existing schemas: TradeSchema, CashTransactionSchema, CorporateActionSchema)
- src/ibkr_tax/models/database.py (existing models: Account, Trade, FIFOLot, CorporateAction)
- src/ibkr_tax/services/flex_parser.py (whitelist, get_unmapped_entities, get_corporate_actions pattern)
- src/ibkr_tax/db/repository.py (import_accounts, import_trades, import_corporate_actions patterns)
- example/U7330779_U7230673_IBKR2KAP_Full_Export_2022.xml (has stock transfer: AEHR, qty=22)
- example/U7330779_U7230673_IBKR2KAP_Full_Export_2024.xml (has stock transfers: MGNT, SIBN, SNGSP)

## XML Transfer Format Reference

**Stock position transfer (direction=IN, receiving account):**
```xml
<Transfer accountId="U7230673" currency="USD" fxRateToBase="0.97643"
    symbol="AEHR" description="AEHR TEST SYSTEMS"
    securityID="US00760J1088" securityIDType="ISIN" isin="US00760J1088"
    type="INTERNAL" direction="IN" quantity="22" transferPrice="0"
    dateTime="20221121;102932" settleDate="20221122"
    account="U7330779" positionAmount="527.164" positionAmountInBase="514.73874452"
    pnlAmount="-36.553858" pnlAmountInBase="-36.553858" cashTransfer="0"
    deliveryType="" />
```

**Cash-only transfer (quantity=0, symbol="--"):**
```xml
<Transfer accountId="U7330779" currency="EUR" fxRateToBase="1" symbol="--"
    description="TRANSFER FROM U7330779 TO U7230673"
    type="INTERNAL" direction="OUT" quantity="0" transferPrice="0"
    dateTime="20230327;034034" settleDate="20230327"
    account="U7230673" cashTransfer="-7000" deliveryType="" />
```

## Tasks

<task type="auto">
  <name>Create TransferSchema in ibkr.py</name>
  <files>src/ibkr_tax/schemas/ibkr.py</files>
  <action>
    Add a new Pydantic schema `TransferSchema(BaseIBKRSchema)` with fields:
    - `account_id: str` — The accountId attribute (which account this record belongs to)
    - `symbol: str` — Security symbol ("--" for cash-only transfers)
    - `description: str` — Human-readable description
    - `currency: str` — Currency of the transferred asset
    - `fx_rate_to_base: Decimal` — FX rate at time of transfer
    - `transfer_type: Literal["INTERNAL"]` — Transfer type (only INTERNAL supported)
    - `direction: Literal["IN", "OUT", "-"]` — Direction of transfer
    - `quantity: Decimal` — Number of shares/units (0 for cash)
    - `transfer_date: date` — Parsed from dateTime (YYYYMMDD part)
    - `settle_date: date` — Settlement date
    - `counterparty_account: str` — The `account` attribute (other account ID)
    - `position_amount: Decimal` — Cost basis in trade currency (positionAmount)
    - `position_amount_in_base: Decimal` — Cost basis in base currency
    - `cash_transfer: Decimal` — Cash amount transferred (0 for stock)
    - `isin: str | None` — ISIN of the transferred security
    - `is_stock_transfer: bool` property — True when quantity != 0 and symbol != "--"

    Add a `to_db_dict()` method following the pattern of existing schemas.

    Do NOT add a float validator override — `BaseIBKRSchema` already has one.
  </action>
  <verify>python -c "from ibkr_tax.schemas.ibkr import TransferSchema; print('OK')"</verify>
  <done>TransferSchema imports successfully with all fields defined</done>
</task>

<task type="auto">
  <name>Create Transfer DB model and add parser + repository support</name>
  <files>
    src/ibkr_tax/models/database.py
    src/ibkr_tax/services/flex_parser.py
    src/ibkr_tax/db/repository.py
    src/ibkr_tax/services/pipeline.py
  </files>
  <action>
    **database.py:**
    - Add `Transfer(Base)` model with table "transfers":
      - id, account_id (FK to accounts.id), symbol, description, currency, fx_rate_to_base,
        transfer_type, direction, quantity, transfer_date, settle_date,
        counterparty_account, position_amount, position_amount_in_base,
        cash_transfer, isin
      - Add UniqueConstraint on (account_id, symbol, transfer_date, direction, quantity) to prevent dupes
    - Add `transfers` relationship to Account model
    - Add `transfer_id` nullable FK to FIFOLot model (for tracing which transfer created a lot)

    **flex_parser.py:**
    - Add `get_transfers()` method using raw ElementTree (same pattern as `get_corporate_actions()`):
      - Parse `<Transfer>` elements from `<Transfers>` containers
      - Extract all attributes, parse dateTime and settleDate
      - Return List[TransferSchema]
    - Add "transfers" key to `parse_all()` return dict
    - Add "Transfers" to the `ignored_tags` set in `get_unmapped_entities()` (since we now handle it)
    - Do NOT add "Transfers" to ibflex_safe_children — ibflex doesn't understand it; we parse via ET

    **repository.py:**
    - Add `import_transfers(session, transfers: List[TransferSchema])` function
      - Follow same pattern as import_corporate_actions
      - Use the unique constraint fields for duplicate detection

    **pipeline.py:**
    - After `import_corporate_actions()`, call `import_transfers()` with parsed transfers
    - Add "transfers" to the return counts dict
  </action>
  <verify>
    python -m pytest tests/test_flex_parser.py -x -v
    python -m pytest tests/test_pipeline.py -x -v
  </verify>
  <done>
    - Transfer model creates table in SQLite
    - FlexXMLParser.get_transfers() returns List[TransferSchema] from XML
    - import_transfers() persists to DB without duplicates
    - parse_all() includes "transfers" key
    - Transfers no longer appear in unmapped entities warnings
  </done>
</task>

## Success Criteria
- [ ] `TransferSchema` validates real XML transfer data without errors
- [ ] `Transfer` DB model creates its table via migrations/create_all
- [ ] `FlexXMLParser.get_transfers()` parses both stock and cash transfers from example XML
- [ ] `import_transfers()` is idempotent (no dupes on re-import)
- [ ] `parse_all()` returns transfers and `Transfers` is no longer an unmapped entity
