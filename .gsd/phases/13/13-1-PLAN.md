---
phase: 13
plan: 1
wave: 1
---

# Plan 13.1: End-to-End Integration

## Objective
Connect all units with an overarching realistic, multi-year end-to-end (e2e) test scenario to evaluate full system correctness.

## Context
- .gsd/SPEC.md
- .gsd/ROADMAP.md
- tests/test_e2e.py (To be created)

## Tasks

<task type="auto">
  <name>Implement end-to-end integration test</name>
  <files>tests/test_e2e.py</files>
  <action>
    Create a comprehensive realistic multi-year e2e test `tests/test_e2e.py`.
    - Set up the SQLite database and initiate required services.
    - Synthesize or use existing mock data representing realistic, multi-year FlexQuery trade histories including standard trading, options expirations/assignments, and cash transactions.
    - Run the complete pipeline sequence end-to-end:
      1. Parsing Data (Flex/CSV fallbacks)
      2. Import Pipeline (Persistence)
      3. ECB Rates Lookups (Mocked for predictability)
      4. Engine Runners (Options, Corporate Actions, FIFO)
      5. Tax Categorization
      6. Excel Generation
    - Assert that final outcomes in the `TaxReport` instance are completely accurate according to German rules.
  </action>
  <verify>pytest tests/test_e2e.py -v</verify>
  <done>The multi-year e2e test executes end-to-end successfully and generates the correct final Anlage KAP aggregates.</done>
</task>

## Success Criteria
- [ ] A new `tests/test_e2e.py` file is created linking the entire application pipeline.
- [ ] The e2e test successfully simulates a multi-year trading scenario with multiple asset/transaction types.
- [ ] `pytest tests/test_e2e.py -v` passes completely.
- [ ] Overall system architectural integrations and correctness are proven.
