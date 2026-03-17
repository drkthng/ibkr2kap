---
phase: 26
plan: 1
wave: 1
---

# Plan 26.1: German Tax Theory Documentation

## Objective
Create a comprehensive reference document (`docs/GERMAN_TAX_THEORY.md`) that explains the German tax rules and Anlage KAP line mappings used by IBKR2KAP. This document serves two audiences:
1. **End users** — Understand what each KAP line means and how their IBKR trades map to German tax law.
2. **Developers** — Understand the legal basis for every tax categorization decision in the codebase.

## Context
- .gsd/SPEC.md (requirements: FIFO, Aktien vs. Sonstige vs. Termingeschäfte, ECB rates, settlement date)
- src/ibkr_tax/services/tax_aggregator.py (current KAP line mapping logic)
- src/ibkr_tax/schemas/report.py (TaxReport schema with KAP fields)
- src/ibkr_tax/services/excel_export.py (Excel sheet structure and German labels)

## Tasks

<task type="auto">
  <name>Create GERMAN_TAX_THEORY.md reference document</name>
  <files>docs/GERMAN_TAX_THEORY.md [NEW]</files>
  <action>
    Create a well-structured Markdown document covering:

    **1. Overview of Anlage KAP**
    - What Anlage KAP is and when German investors must file it
    - Role of the 801€/1602€ Sparerfreibetrag (saver's allowance)
    - Note that IBKR does NOT withhold German Abgeltungsteuer (unlike domestic banks)

    **2. Line-by-Line Breakdown (Lines 7, 8, 9, 10, 15)**
    - Line 7: Kapitalerträge — dividends, interest, Payment in Lieu of Dividends, Sonstige (ETFs, bonds) gains
    - Line 8: Gewinne aus Aktienveräußerungen — positive realized gains from stock sales (§ 20 Abs. 2 EStG), categorized as "Aktien" tax pool
    - Line 9: Verluste aus Aktienveräußerungen — absolute value of negative realized PnL from stock sales, reported separately because stock losses can ONLY offset stock gains (Aktienverlusttopf)
    - Line 10: Termingeschäfte — net gains/losses from options and futures (§ 20 Abs. 2 Nr. 3 EStG). Note: the 20k loss limitation was repealed by JStG 2024
    - Line 15: Anrechenbare ausländische Steuern — foreign withholding taxes paid, claimable as tax credit

    **3. Tax Pool Separation Rules**
    - Aktienverlusttopf vs. allgemeiner Verlusttopf
    - Why stock losses are ring-fenced (§ 20 Abs. 6 S. 5 EStG)
    - Termingeschäfte separation rules

    **4. FIFO Principle (§ 20 Abs. 4 S. 7 EStG)**
    - What First-In-First-Out means for cost basis calculation
    - Why settlement date (Valuta) is used, not trade date
    - Example: buy 100 shares on Day 1, buy 50 on Day 2, sell 120 → cost basis comes from all Day 1 + 20 from Day 2

    **5. FX Conversion Rules**
    - ECB reference rate requirement
    - Weekend/holiday fallback (last available business day rate)
    - FX gains on currency holdings (§ 23 Abs. 1 Nr. 2 EStG — "private Veräußerungsgeschäfte")
    - 1-year holding period exemption for FX gains

    **6. Corporate Actions**
    - Stock splits: cost basis is redistributed, no taxable event
    - Reverse splits with symbol/ISIN change: same principle, cost basis consolidation
    - Spinoffs: cost basis allocation between parent and child

    **7. Options Handling**
    - Expiry = full loss/gain realized
    - Exercise/Assignment = premium folds into stock cost basis (no separate gain/loss event)
    - Categorization as Termingeschäfte

    **8. Disclaimer**
    - This is not tax advice
    - Consult a Steuerberater for individual situations
    - Laws referenced as of 2024/2025

    DO NOT:
    - Include actual code snippets — this is a tax theory reference, not a developer guide
    - Write in English where German tax terms exist — use original German terms with English explanations
    - Make definitive tax advice claims — always frame as "how IBKR2KAP interprets the rules"
  </action>
  <verify>Test-Path "docs/GERMAN_TAX_THEORY.md"</verify>
  <done>docs/GERMAN_TAX_THEORY.md exists with all 8 sections, readable and well-formatted</done>
</task>

<task type="auto">
  <name>Create KAP_LINE_TOOLTIPS constant for UI reuse</name>
  <files>src/ibkr_tax/services/tax_tooltips.py [NEW]</files>
  <action>
    Create a small Python module that holds tooltip/help text for each KAP line, intended for reuse in the Streamlit UI. This centralizes the user-facing explanations.

    Define a dictionary `KAP_TOOLTIPS` with keys matching the report field names:
    - `kap_line_7`: Short explanation of what Line 7 contains (Kapitalerträge = dividends + interest + Sonstige gains)
    - `kap_line_8`: What Line 8 is (positive stock gains only)
    - `kap_line_9`: What Line 9 is (absolute stock losses, ring-fenced)
    - `kap_line_10`: What Line 10 is (net Termingeschäfte result)
    - `kap_line_15`: What Line 15 is (creditable foreign taxes)
    - `total_realized_pnl`: What the total represents

    Also define a `TAX_POOL_EXPLANATIONS` dictionary:
    - `Aktien`: Explanation of the Aktienverlusttopf
    - `Termingeschäfte`: Explanation of the Termingeschäfte pool
    - `Sonstige`: Explanation of the general pool

    Each tooltip should be 1-3 sentences in plain German with English terms in parentheses where helpful.

    DO NOT:
    - Import any heavy dependencies — this is just a constants module
    - Make this dependent on any other module — it's a standalone reference
  </action>
  <verify>python -c "from ibkr_tax.services.tax_tooltips import KAP_TOOLTIPS, TAX_POOL_EXPLANATIONS; assert len(KAP_TOOLTIPS) >= 5; assert len(TAX_POOL_EXPLANATIONS) >= 3; print('OK')"</verify>
  <done>tax_tooltips.py is importable, contains KAP_TOOLTIPS with 5+ entries and TAX_POOL_EXPLANATIONS with 3+ entries</done>
</task>

## Success Criteria
- [ ] `docs/GERMAN_TAX_THEORY.md` exists with all 8 sections and is well-structured
- [ ] `src/ibkr_tax/services/tax_tooltips.py` is importable and contains the tooltip data
- [ ] No existing tests broken (run: `uv run pytest tests/ -x`)
