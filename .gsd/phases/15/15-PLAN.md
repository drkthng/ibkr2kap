---
phase: 15
plan: 1
wave: 1
---

# Plan 15.1: XML Ingestion Error Reporting

## Objective
Detect unknown entities/models during Flex Query XML parsing and return formatted info-messages with the entity type and file location visually in the Streamlit UI. This way, users are aware if their XML file contains data that our system is currently ignoring.

## Context
- .gsd/SPEC.md
- src/ibkr_tax/services/flex_parser.py
- src/ibkr_tax/services/pipeline.py
- src/app.py

## Tasks

<task type="auto">
  <name>Detect Unmapped XML Entities in Parser</name>
  <files>
    - src/ibkr_tax/services/flex_parser.py
  </files>
  <action>
    - Update `FlexXMLParser` to parse the raw XML data (e.g., using `xml.etree.ElementTree` or iterating over lines) to find child node tags of `FlexStatement`.
    - Define a set of `SUPPORTED_ENTITIES` (e.g., `AccountInformation`, `Trades`, `CashTransactions`, `OptionEAE`, `CorporateActions`, `OpenPositions`, `EquitySummaryByDividendDate` etc, check exactly what ibflex `FlexStatement` maps or what we care about). Only trigger a warning if an entity is completely unhandled by our pipeline and not purely informational noise. 
    - Specifically, anything that could contain financial transactions should be checked, or just dynamically list any tag immediately inside `<FlexStatement>` that we do not map in `parse_all()`.
    - Return a list of dictionary warnings like `{"entity": "EntityName", "location": "Under Account XYZ"}` from `parse_all()`.
  </action>
  <verify>pytest src/tests/ -k "test_flex_parser"</verify>
  <done>FlexXMLParser successfully returns a list of unmapped entity warnings when parsing an XML with unknown tags.</done>
</task>

<task type="auto">
  <name>Display Warnings in Streamlit UI</name>
  <files>
    - src/ibkr_tax/services/pipeline.py
    - src/app.py
  </files>
  <action>
    - Update `run_import()` in `pipeline.py` to extract these warnings from `parser.parse_all()` and include them in the returned dictionary under a `warnings` key.
    - Update `app.py` in the "Data Import" tab. If the result from `run_import` contains `warnings`, iterate through them and display a `st.warning()` for each, instructing the user about the unknown entity and its location.
  </action>
  <verify>python -m pytest src/tests/ -k "test_pipeline"</verify>
  <done>The pipeline dictionary contains warnings and Streamlit UI has logic to display `st.warning` messages.</done>
</task>

## Success Criteria
- [ ] Processing an XML with unsupported entities triggers a warning containing the entity name.
- [ ] Users can see this warning clearly directly in the "Data Import" tab of the Streamlit UI upon successful upload.
