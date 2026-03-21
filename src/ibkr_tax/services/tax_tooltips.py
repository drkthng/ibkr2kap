"""
Tooltip and help texts for German tax (Anlage KAP) fields.

This module centralizes all user-facing explanations for the Streamlit UI.
It has no external dependencies — it's a standalone constants reference.
"""

KAP_TOOLTIPS: dict[str, dict[str, str]] = {
    "de": {
        "kap_line_7": (
            "Zeile 7 — Kapitalerträge: Summe aus Dividenden, Zinsen (inkl. Broker Interest Received) und "
            "Gewinnen/Verlusten aus sonstigen Wertpapieren (z. B. ETFs, Anleihen). "
            "Margin-Zinsen (Broker Interest Paid) sind gemäß § 20 Abs. 9 EStG "
            "nicht abzugsfähig und daher NICHT enthalten."
        ),
        "kap_line_8": (
            "Zeile 8 — Gewinne aus Aktienveräußerungen: Nur die positiven "
            "realisierten Gewinne aus dem Verkauf von Einzelaktien. "
            "ETFs und Fonds zählen nicht als Aktien im steuerlichen Sinne."
        ),
        "kap_line_9": (
            "Zeile 9 — Verluste aus Aktienveräußerungen (Absolutwert): "
            "Diese Verluste können ausschließlich mit Aktiengewinnen (Zeile 8) "
            "verrechnet werden (Aktienverlusttopf, § 20 Abs. 6 S. 5 EStG)."
        ),
        "kap_line_10": (
            "Zeile 10 — Termingeschäfte (netto): Gewinne minus Verluste aus "
            "Optionen und Futures. Die 20.000 €-Verlustbegrenzung wurde durch "
            "das JStG 2024 rückwirkend aufgehoben."
        ),
        "kap_line_15": (
            "Zeile 15 — Anrechenbare ausländische Steuern: Im Ausland "
            "einbehaltene Quellensteuern auf Dividenden/Zinsen. "
            "Können auf die deutsche Steuer angerechnet werden (§ 32d Abs. 5 EStG)."
        ),
        "aktien_net_result": (
            "Aktientopf (Netto): Das steuerliche Ergebnis aller Aktienveräußerungen (Zeile 8 minus Zeile 9). "
            "Dieser Topf ist isoliert: Verluste können nur mit Aktiengewinnen verrechnet werden."
        ),
        "allgemeiner_topf_result": (
            "Allgemeiner Topf: Das kombinierte Ergebnis aus Dividenden, Zinsen, sonstigen Gewinnen (ETFs) "
            "und Termingeschäften (Optionen/Futures). Diese Erträge können untereinander verrechnet werden."
        ),
    },
    "en": {
        "kap_line_7": (
            "Line 7 — Capital Gains: Sum of dividends, interest (incl. Broker Interest Received) and "
            "gains/losses from other securities (e.g. ETFs, bonds). "
            "Margin interest (Broker Interest Paid) is NOT deductible according to § 20 Abs. 9 EStG "
            "and therefore NOT included."
        ),
        "kap_line_8": (
            "Line 8 — Gains from Stock Sales: Only positive realized gains from the sale of individual stocks. "
            "ETFs and funds do not count as stocks for tax purposes."
        ),
        "kap_line_9": (
            "Line 9 — Losses from Stock Sales (Absolute Value): These losses can only be offset against "
            "stock gains (Line 8) (Stock Loss Pool, § 20 Abs. 6 S. 5 EStG)."
        ),
        "kap_line_10": (
            "Line 10 — Derivatives (Net): Gains minus losses from options and futures. The €20,000 loss "
            "limit was retroactively abolished by the JStG 2024."
        ),
        "kap_line_15": (
            "Line 15 — Creditable Foreign Taxes: Withholding taxes withheld abroad on dividends/interest. "
            "Can be credited against German tax (§ 32d Abs. 5 EStG)."
        ),
        "aktien_net_result": (
            "Stock Pool (Net): The tax result of all stock sales (Line 8 minus Line 9). "
            "This pool is isolated: losses can only be offset against stock gains."
        ),
        "allgemeiner_topf_result": (
            "General Pool: The combined result of dividends, interest, other gains (ETFs) "
            "and derivatives (options/futures). These yields can be offset against each other."
        ),
    }
}

TAX_POOL_EXPLANATIONS: dict[str, dict[str, str]] = {
    "de": {
        "Aktien": (
            "Aktienverlusttopf: Verluste aus Aktienverkäufen können nur mit "
            "Gewinnen aus Aktienverkäufen verrechnet werden. Nicht verrechnete "
            "Verluste werden in Folgejahre vorgetragen. "
            "(§ 20 Abs. 6 Satz 5 EStG)"
        ),
        "Termingeschäfte": (
            "Termingeschäfte-Topf: Gewinne und Verluste aus Optionen und Futures "
            "werden separat erfasst. Die durch das JStG 2020 eingeführte "
            "Verlustbegrenzung auf 20.000 € wurde durch das JStG 2024 aufgehoben."
        ),
        "Sonstige": (
            "Allgemeiner Verlusttopf: Gewinne und Verluste aus ETFs, Anleihen "
            "und sonstigen Kapitalanlagen. Diese können frei mit Dividenden "
            "und Zinsen verrechnet werden und fließen in Zeile 7 der Anlage KAP."
        ),
    },
    "en": {
        "Aktien": (
            "Stock Loss Pool: Losses from stock sales can only be offset against "
            "gains from stock sales. Unused losses are carried forward to future years. "
            "(§ 20 Abs. 6 Sentence 5 EStG)"
        ),
        "Termingeschäfte": (
            "Derivatives Pool: Gains and losses from options and futures are "
            "recorded separately. The €20,000 loss limit introduced by JStG 2020 "
            "was abolished by JStG 2024."
        ),
        "Sonstige": (
            "General Loss Pool: Gains and losses from ETFs, bonds, and other capital "
            "investments. These can be freely offset against dividends and interest "
            "and flow into Line 7 of Anlage KAP."
        ),
    }
}
