---
phase: 25
plan: 1
wave: 1
---

# Phase 25, Plan 1: Schema & Parser Updates for FS + Reverse Split Grouping

## Objective
Add `FS` (Forward Split) to the action_type Literal. Implement a grouping function in `flex_parser.py` that clusters related RS/FS records into logical split events, detecting the symbol rename pattern (e.g., DEC→DEC.OLD).

## Tasks

### 1. Add `FS` to `CorporateActionSchema.action_type`
Allow the `FS` type used by IBKR for forward splits in 2024+ exports.
- **File**: `src/ibkr_tax/schemas/ibkr.py`
- Update Literal from `"SO", "RS", "RI", "DW", "DI", "ED"` to include `"FS"`
- Also assign `"NEUTRAL_SPLIT"` tax_treatment for `FS` in `flex_parser.py` (line 230)
- **Verify**: `pytest tests/test_corporate_actions.py`

### 2. Create `group_split_actions()` helper in `flex_parser.py`
After parsing all CorporateAction elements, group RS/FS records that share the same `(date, parent_symbol, description_pattern)` into a single logical split event. This function should:
- Detect the "remove old (.OLD symbol, negative qty)" + "add new (positive qty)" pattern
- Calculate the ratio from total old_qty / total new_qty
- Return a single synthetic `CorporateActionSchema` record per logical split with the correct `new_symbol`, `ratio`, and `total_quantity`
- **File**: `src/ibkr_tax/services/flex_parser.py`
- **Verify**: New test `tests/test_flex_parser_split_grouping.py`

## Success Criteria
- [ ] `FS` type accepted in schema validation
- [ ] DEC reverse split (4 records) grouped into 1 logical event with ratio 1/20 = 0.05
- [ ] Forward split records grouped correctly (e.g., 2 FOR 1 ratio = 2.0)
