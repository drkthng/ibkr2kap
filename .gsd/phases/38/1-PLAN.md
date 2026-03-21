---
phase: 38
plan: 1
wave: 1
---

# Plan 38.1: Termingeschäfte Granular Reporting

## Objective
Split the reporting of "Termingeschäfte" into three distinct fields: Gains (Gewinne), Losses (Verluste), and the overall net Result. This split must be reflected in the internal tax modeling, the Streamlit UI, and the Excel export.

## Context
- .gsd/SPEC.md
- src/ibkr_tax/schemas/report.py
- src/ibkr_tax/services/tax_aggregator.py
- src/ibkr_tax/services/excel_export.py
- src/app.py

## Tasks

<task type="auto">
  <name>Schema and Aggregator Updates</name>
  <files>
    - src/ibkr_tax/schemas/report.py
    - src/ibkr_tax/services/tax_aggregator.py
    - tests/test_tax_aggregator.py
  </files>
  <action>
    - In `schemas/report.py`, add `kap_termingeschaefte_gains` and `kap_termingeschaefte_losses` (both `Decimal`) to `TaxReport` and `CombinedTaxReport`.
    - In `services/tax_aggregator.py`, within `generate_report`, split `g.realized_pnl` for the `Termingeschäfte` tax pool: if > 0 add to gains, if < 0 add to losses (absolute value or leave negative depending on existing logic convention, usually keep negative for losses but ensure UI logic knows). The net goes to `kap_line_10_termingeschaefte`.
    - Also update `generate_combined_report` to aggregate these new fields.
    - Update `test_tax_aggregator.py` to assert these new fields calculate correctly.
  </action>
  <verify>pytest tests/test_tax_aggregator.py</verify>
  <done>TaxAggregatorService successfully splits Termingeschäfte into gains and losses, tests pass.</done>
</task>

<task type="auto">
  <name>UI and Export Implementations</name>
  <files>
    - src/ibkr_tax/services/excel_export.py
    - src/app.py
    - tests/test_excel_export.py
  </files>
  <action>
    - In `excel_export.py`, modify `_add_summary_sheet` to output three rows for Termingeschäfte under the KAP section instead of one (Gewinne, Verluste, Netto).
    - In `app.py`, update the metrics section to display all three values (e.g., in adjacent UI columns or stacked metrics).
    - Update `test_excel_export.py` or existing UI tests if applicable to expect these new fields/labels.
  </action>
  <verify>pytest</verify>
  <done>Excel export and Streamlit UI show gains, losses, and net for Termingeschäfte, all tests pass.</done>
</task>

## Success Criteria
- [ ] `TaxReport` schema includes distinct gains/losses fields for Termingeschäfte.
- [ ] The Excel export's summary page displays Gains, Losses, and the Net value on separate lines.
- [ ] The Streamlit UI displays the 3 components clearly in the summary tab.
- [ ] All unit and integration tests pass flawlessly without regression.
