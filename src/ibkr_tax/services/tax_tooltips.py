"""
Tooltip and help texts for German tax (Anlage KAP) fields.

This module centralizes all user-facing explanations for the Streamlit UI.
It has no external dependencies — it's a standalone constants reference.
"""

KAP_TOOLTIPS: dict[str, str] = {
    "kap_line_7": (
        "Zeile 7 — Kapitalerträge: Summe aus Dividenden, Zinsen und "
        "Gewinnen/Verlusten aus sonstigen Wertpapieren (z. B. ETFs, Anleihen). "
        "Aktienergebnisse und Termingeschäfte gehören nicht hierher."
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
    "total_realized_pnl": (
        "Gesamt realisierter Gewinn/Verlust: Summe aller realisierten "
        "Ergebnisse aus Wertpapierverkäufen vor Steuer, über alle Tax Pools hinweg."
    ),
}

TAX_POOL_EXPLANATIONS: dict[str, str] = {
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
}
