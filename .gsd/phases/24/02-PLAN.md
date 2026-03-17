---
phase: 24
plan: 2
wave: 2
---

# Phase 24, Plan 2: XML Parser Implementation

Implement raw XML parsing for the `<CorporateActions>` section in `FlexXMLParser`.

## Tasks

### 1. Implement `get_corporate_actions`
Use `xml.etree.ElementTree` to parse the `CorporateActions` section.
- **File**: `src/ibkr_tax/services/flex_parser.py`
- **Verify**: New test `tests/test_flex_parser_corporate_actions.py`

### 2. Regex Extraction for Parent Symbols
Implement robust regex to extract parent symbols from corporate action descriptions.
- **File**: `src/ibkr_tax/services/flex_parser.py`

## Verification
- `uv run pytest tests/test_flex_parser_corporate_actions.py`
