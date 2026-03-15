---
phase: 4
plan: 1
wave: 1
---

# Plan 4.1: Flex Query XML Parser

## Objective
Create a service that uses `ibflex` to parse an IBKR XML Flex Query and returns a structured output mapped to our strict Pydantic schemas (AccountSchema, TradeSchema, CashTransactionSchema).

## Context
- .gsd/SPEC.md
- .gsd/ROADMAP.md
- .gsd/phases/4/RESEARCH.md
- src/ibkr_tax/schemas/ibkr.py

## Tasks

<task type="auto">
  <name>Implement FlexXMLParser</name>
  <files>src/ibkr_tax/services/flex_parser.py</files>
  <action>
    Create a `FlexXMLParser` class/function that:
    - Takes a file path or string content of an XML file.
    - Uses `ibflex.parser.parse()` to read the XML.
    - Iterates over `FlexStatements` and extracts Account info, Trades, and CashTransactions.
    - Converts the extracted records into our Pydantic schemas from `src.ibkr_tax.schemas.ibkr`.
    - Returns a structured dictionary/class containing lists of valid Pydantic models.
  </action>
  <verify>pytest</verify>
  <done>FlexXMLParser returns fully validated Pydantic models for Trades and CashTransactions.</done>
</task>

<task type="auto">
  <name>Write tests for FlexXMLParser</name>
  <files>tests/test_flex_parser.py</files>
  <action>
    Write tests using `pytest` to verify the parser.
    - Use a robust, small fixture or the provided XMLs in `example/`.
    - Test the parsing of Trades and CashTransactions (dividends, taxes, fees).
    - Assert that all mandatory Pydantic fields correctly map from the ibflex attributes and that types (Decimal, Date) are respected.
  </action>
  <verify>pytest tests/test_flex_parser.py -v</verify>
  <done>Tests pass with high coverage, demonstrating accurate XML to Pydantic transformation.</done>
</task>

## Success Criteria
- [ ] `ibflex` module successfully parses example XML inputs without errors.
- [ ] The returned data successfully passes Pydantic validations (AccountSchema, TradeSchema, CashTransactionSchema).
- [ ] Tests confirm that the fields map accurately and no data validation errors arise for standard attributes.
