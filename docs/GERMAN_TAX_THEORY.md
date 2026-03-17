# German Tax Theory Reference — IBKR2KAP

> **Hinweis / Disclaimer**: Dieses Dokument stellt **keine Steuerberatung** dar.
> Es beschreibt lediglich, wie IBKR2KAP die geltenden Steuerregeln interpretiert und umsetzt.
> Für individuelle Fragen wenden Sie sich bitte an einen **Steuerberater**.
>
> Rechtsstand: **2024/2025** (unter Berücksichtigung des JStG 2024).

---

## 1. Überblick: Anlage KAP

Die **Anlage KAP** (Kapitalerträge) ist die Anlage zur deutschen Einkommensteuererklärung, in der
alle Einkünfte aus Kapitalvermögen erklärt werden — also Zinsen, Dividenden und
Veräußerungsgewinne aus Wertpapiergeschäften.

### Wann muss ich die Anlage KAP ausfüllen?

Deutsche Privatanleger, die über **Interactive Brokers (IBKR)** handeln, müssen die Anlage KAP
**immer** ausfüllen, weil:

- IBKR als ausländischer Broker **keine deutsche Abgeltungsteuer** (25 % + Soli + ggf. KiSt) einbehält.
- Die Kapitalerträge sind daher nur im Rahmen der Einkommensteuererklärung zu versteuern.
- Der **Sparer-Pauschbetrag** (Sparerfreibetrag) von **1.000 € / 2.000 €** (Ledige / Zusammenveranlagte)
  muss vom Anleger selbst geltend gemacht werden.

> **Zum Vergleich**: Inländische Banken (z. B. ING, Commerzbank) führen die Abgeltungsteuer
> automatisch ab und berücksichtigen den Freistellungsauftrag automatisch.

---

## 2. Die KAP-Zeilen im Detail

IBKR2KAP berechnet folgende Zeilen der Anlage KAP:

### Zeile 7 — Kapitalerträge (allgemein)

**Inhalt**: Erträge, die nicht in andere Spezialzeilen gehören:
- **Dividenden** (einschließlich „Payment In Lieu of Dividends")
- **Zinsen** aus Broker-Guthaben
- **Sonstige Veräußerungsgewinne** — z. B. aus ETF-, Anleihe- oder Fondsverkäufen
  (alles, was weder „Aktie" noch „Termingeschäft" ist)

**Rechtsgrundlage**: § 20 Abs. 1 und § 20 Abs. 2 Nr. 1, 7 EStG

### Zeile 8 — Gewinne aus Aktienveräußerungen

**Inhalt**: Die Summe aller **positiven** realisierten Gewinne aus dem Verkauf von Einzelaktien.

- Nur Aktien im engeren Sinne (Stammaktien, Vorzugsaktien), keine ETFs oder Fonds
- IBKR2KAP verwendet den **Tax Pool „Aktien"** für diese Zuordnung

**Rechtsgrundlage**: § 20 Abs. 2 Satz 1 Nr. 1 EStG

### Zeile 9 — Verluste aus Aktienveräußerungen

**Inhalt**: Die Summe aller **negativen** realisierten Ergebnisse aus dem Verkauf von Einzelaktien
(als **Absolutwert** angegeben).

**Warum getrennt?** Aktienverluste dürfen **nur** mit Aktiengewinnen verrechnet werden
(Aktienverlusttopf, § 20 Abs. 6 Satz 5 EStG). Sie können nicht mit Dividenden, Zinsen oder
sonstigen Gewinnen verrechnet werden. Nicht ausgeschöpfte Aktienverluste werden in
Folgejahre vorgetragen.

**Rechtsgrundlage**: § 20 Abs. 6 Satz 5 EStG

### Zeile 10 — Termingeschäfte

**Inhalt**: **Netto**-Ergebnis (Gewinne minus Verluste) aus Termingeschäften:
- Optionen (Calls, Puts) — Kauf, Verkauf, Verfall
- Futures

**Wichtig — JStG 2024**: Die ursprünglich im JStG 2020 eingeführte **Verlustbegrenzung auf
20.000 € pro Jahr** für Termingeschäfte wurde durch das **Jahressteuergesetz 2024** rückwirkend
aufgehoben. IBKR2KAP berechnet daher das volle Netto-Ergebnis ohne Begrenzung.

**Rechtsgrundlage**: § 20 Abs. 2 Nr. 3 EStG; § 20 Abs. 6 Satz 5 i. d. F. JStG 2024

### Zeile 15 — Anrechenbare ausländische Steuern (Quellensteuer)

**Inhalt**: Im Ausland einbehaltene Quellensteuern auf Dividenden und Zinsen.

- IBKR meldet diese als negativen Betrag (Geldabfluss)
- Für die Anlage KAP wird der **Absolutwert** eingetragen
- Die Quellensteuer kann auf die deutsche Abgeltungsteuer **angerechnet** werden

**Rechtsgrundlage**: § 32d Abs. 5 EStG; DBA-Regelungen

---

## 3. Verlusttöpfe (Tax Pools)

Das deutsche Steuerrecht trennt Kapitalverluste in verschiedene „Töpfe":

### Aktienverlusttopf (Zeilen 8 / 9)

| Eigenschaft | Regel |
|---|---|
| **Verrechenbar mit** | Ausschließlich Gewinnen aus Aktienveräußerungen |
| **Nicht verrechenbar mit** | Dividenden, Zinsen, ETF-Gewinnen, Termingeschäften |
| **Vortrag** | Nicht ausgeschöpfte Verluste werden in Folgejahre vorgetragen |
| **Rechtsgrundlage** | § 20 Abs. 6 Satz 5 EStG |

Wer in einem Jahr z. B. 5.000 € Aktiengewinn und 8.000 € Aktienverlust hat, kann 5.000 €
sofort verrechnen. Die restlichen 3.000 € Verlust werden vorgetragen.

### Termingeschäfte-Topf (Zeile 10)

| Eigenschaft | Regel |
|---|---|
| **Verrechenbar mit** | Gewinnen aus Termingeschäften |
| **20k-Grenze** | **Aufgehoben** durch JStG 2024 |
| **Rechtsgrundlage** | § 20 Abs. 6 Satz 5 EStG i. d. F. JStG 2024 |

### Allgemeiner Verlusttopf (Sonstige)

Gewinne und Verluste aus ETFs, Anleihen, Fonds usw. können frei mit Dividenden und Zinsen
verrechnet werden (fließen alle in Zeile 7).

---

## 4. FIFO-Prinzip

### Was bedeutet FIFO?

**First-In-First-Out** (§ 20 Abs. 4 Satz 7 EStG): Bei der Ermittlung des Veräußerungsgewinns wird
unterstellt, dass die **zuerst angeschafften** Wertpapiere auch **zuerst veräußert** werden.

### Warum Settle-Date (Valutadatum)?

IBKR2KAP verwendet das **Settlement-Datum** (Valuta), nicht das Trade-Datum, für die
steuerliche Zuordnung:

- Das Settlement-Datum bestimmt, in welches **Steuerjahr** ein Geschäft fällt
- Bei Aktien liegt das Settlement i. d. R. **T+2** (zwei Geschäftstage nach dem Handelstag)
- Ein Trade am 30.12.2023 mit Settlement am 03.01.2024 gehört steuerlich ins **Jahr 2024**

### Beispiel

| Datum | Aktion | Menge | Kurs |
|---|---|---|---|
| 01.03. | Kauf | 100 Stk. | 50 € |
| 15.05. | Kauf | 50 Stk. | 55 € |
| 10.08. | Verkauf | 120 Stk. | 60 € |

**FIFO-Zuordnung des Verkaufs**:
- 100 Stk. aus Kauf vom 01.03. → Anschaffungskosten: 100 × 50 € = **5.000 €**
- 20 Stk. aus Kauf vom 15.05. → Anschaffungskosten: 20 × 55 € = **1.100 €**
- Veräußerungserlös: 120 × 60 € = **7.200 €**
- **Gewinn**: 7.200 € – 6.100 € = **1.100 €**

---

## 5. Währungsumrechnung (FX)

### ECB-Referenzkurse

Für die Umrechnung von Fremdwährungsbeträgen in Euro verwendet IBKR2KAP die
offiziellen **EZB-Referenzkurse** (European Central Bank).

- Am **Handelstag** (bzw. Settlementtag) gültiger Kurs
- An **Wochenenden und Feiertagen** wird der letzte verfügbare Geschäftstagskurs verwendet
  (Rückfallmechanismus)

### Währungsgewinne (§ 23 Abs. 1 Nr. 2 EStG)

Gewinne aus dem **Halten und Umtauschen von Fremdwährung** sind als
„private Veräußerungsgeschäfte" steuerrelevant, sofern die **Haltefrist unter einem Jahr** liegt.

| Haltefrist | Steuerliche Behandlung |
|---|---|
| < 1 Jahr | **Steuerpflichtig** als privates Veräußerungsgeschäft (§ 23 EStG) |
| ≥ 1 Jahr | **Steuerfrei** |

IBKR2KAP berechnet die Haltefrist automatisch per FIFO auf die Währungsbestände und
kennzeichnet FX-Gewinne im Excel-Export als „JA" oder „NEIN" (steuerrelevant nach § 23).

> **Hinweis**: Diese Gewinne gehören **nicht** in die Anlage KAP, sondern in die
> **Anlage SO** (Sonstige Einkünfte). Sie werden im Excel-Export dennoch ausgewiesen,
> damit der Steuerberater alle relevanten Daten hat.

---

## 6. Kapitalmaßnahmen (Corporate Actions)

### Aktiensplits (Forward Splits)

- **Kein steuerpflichtiger Vorgang** — es findet kein Zufluss statt
- Die bestehenden Anschaffungskosten werden auf die neue Stückzahl über den Splitfaktor verteilt
- Beispiel: 100 Aktien à 200 € → Split 2:1 → 200 Aktien à 100 €
  (Anschaffungskosten bleiben 20.000 €)

### Reverse Splits (Aktienzusammenlegung)

- Ebenfalls **kein steuerpflichtiger Vorgang**
- Anschaffungskosten werden auf die reduzierte Stückzahl zusammengeführt
- Bei gleichzeitiger **Symbol-/ISIN-Änderung** führt IBKR2KAP die Umschlüsselung automatisch durch

### Spinoffs (Abspaltungen)

- Die Anschaffungskosten der Mutteraktie werden anteilig auf Mutter- und Tochteraktie aufgeteilt
- IBKR2KAP verwendet den von IBKR gemeldeten Allokationsfaktor
- **Kein steuerpflichtiger Vorgang** zum Zeitpunkt des Spinoffs — erst beim späteren Verkauf
  wird der anteilige Gewinn realisiert

---

## 7. Optionen

### Zuordnung: Termingeschäfte (Tax Pool)

Optionen gelten steuerlich als **Termingeschäfte** (§ 20 Abs. 2 Nr. 3 EStG) und werden
in Zeile 10 der Anlage KAP erfasst.

### Verfall (Expiry)

- **Verkaufte Option verfällt**: Der erhaltene Prämienerlös ist ein realisierter **Gewinn**
- **Gekaufte Option verfällt**: Die gezahlte Prämie ist ein realisierter **Verlust**
- Die Gewinn/Verlust-Realisierung erfolgt am Verfallsdatum

### Ausübung / Zuteilung (Exercise / Assignment)

- Bei Ausübung oder Zuteilung wird **kein separater Gewinn/Verlust** aus der Option realisiert
- Die Optionsprämie wird stattdessen in die **Anschaffungskosten der zugrundeliegenden Aktie**
  eingerechnet (Anpassung der Cost Basis)

| Situation | Behandlung |
|---|---|
| Call-Verkauf → Assignment | Prämie erhöht den Veräußerungserlös der Aktien |
| Put-Verkauf → Assignment | Prämie mindert die Anschaffungskosten der Aktien |
| Call-Kauf → Exercise | Prämie erhöht die Anschaffungskosten der Aktien |
| Put-Kauf → Exercise | Prämie mindert den Veräußerungserlös der Aktien |

---

## 8. Haftungsausschluss / Disclaimer

> ⚠️ **Dieses Dokument und die Software IBKR2KAP stellen keine Steuerberatung dar.**
>
> Die dargestellten Informationen geben die Interpretation der Autoren zum aktuellen
> Rechtsstand (2024/2025) wieder. Steuergesetze und deren Auslegung können sich ändern.
>
> Für die Richtigkeit und Vollständigkeit wird keine Haftung übernommen. Bei individuellen
> steuerlichen Fragen konsultieren Sie bitte einen zugelassenen **Steuerberater
> (Steuerberater / Wirtschaftsprüfer)**.
>
> **Referenzierte Gesetze:**
> - Einkommensteuergesetz (EStG), insbesondere §§ 20, 23, 32d
> - Jahressteuergesetz 2024 (JStG 2024)
> - Abgeltungsteuer: § 32d EStG
> - Doppelbesteuerungsabkommen (DBA) für Quellensteuer
