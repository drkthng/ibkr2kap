Deep Research: IBKR-Steuerreport-App – Tech-Stack, Architektur & Entwicklungsplan
1. Analyse der IBKR-Datenformate
Bevor wir den Tech-Stack festlegen, müssen wir verstehen, was IBKR uns liefert:

1.1 Activity Statement (CSV)
Das Standard-Format. Problem: Es ist kein echtes CSV, sondern ein Multi-Section-Dokument:


Statement,Header,Field Name,Field Value
Statement,Data,BrokerName,Interactive Brokers
...
Trades,Header,DataDiscriminator,Asset Category,Currency,Symbol,Date/Time,Quantity,T. Price,Proceeds,Comm/Fee,...
Trades,Data,Order,Stocks,USD,AAPL,2024-03-15 10:30:00,100,175.50,17550.00,-1.00,...
Trades,Data,Order,Stocks,USD,AAPL,2024-08-20 14:15:00,-100,225.00,-22500.00,-1.00,...
Trades,SubTotal,,Stocks,USD,,,,,...
Trades,Data,Order,Equity and Index Options,USD,SPY 240315P00500000,...
...
Dividends,Header,Currency,Date,Description,Amount
Dividends,Data,USD,2024-06-15,AAPL (US0378331005) Cash Dividend 0.25 per Share,25.00
...
Withholding Tax,Header,Currency,Date,Description,Amount
Withholding Tax,Data,USD,2024-06-15,AAPL (US0378331005) Cash Dividend,-3.75
Parsing-Schwierigkeiten:

Jede Section hat eigene Spalten
SubTotal- und Total-Zeilen sind mit Daten vermischt
Options-Symbole enthalten Kommas in Descriptions
Corporate Actions sind schwer zu parsen
1.2 Flex Query (XML) – Empfehlung als primäres Format
XML

<FlexQueryResponse>
  <FlexStatements>
    <FlexStatement accountId="U1234567" fromDate="2020-01-01" toDate="2024-12-31">
      <Trades>
        <Trade symbol="AAPL" dateTime="2024-03-15;103000" 
               quantity="100" tradePrice="175.50" proceeds="17550" 
               ibCommission="-1.0" currency="USD" 
               assetCategory="STK" settleDateTarget="2024-03-18"
               openCloseIndicator="O" buySell="BUY" />
      </Trades>
      <CorporateActions>...</CorporateActions>
      <Dividends>...</Dividends>
      <WithholdingTax>...</WithholdingTax>
    </FlexStatement>
  </FlexStatements>
</FlexQueryResponse>
Vorteile: Strukturiert, typisiert, es gibt eine fertige Python-Bibliothek (ibflex).

1.3 Empfehlung
Kriterium	CSV Activity Statement	Flex Query XML
Parsing-Aufwand	Hoch (custom parser nötig)	Niedrig (ibflex Bibliothek)
Zuverlässigkeit	Fragil (Format ändert sich)	Robust (stabile API)
Automatisierung	Manueller Download	API-Abruf möglich
Datenqualität	SubTotals müssen gefiltert werden	Saubere Einzeldaten
→ Primär: Flex Query XML mit ibflex-Bibliothek
→ Sekundär (Phase 2): CSV-Parser als Fallback

2. Tech-Stack-Empfehlung
2.1 Übersicht

┌─────────────────────────────────────────────────┐
│                    Frontend                       │
│              Streamlit (Phase 1)                  │
│         React + FastAPI (optional Phase 2)        │
├─────────────────────────────────────────────────┤
│                 Business Logic                    │
│  Python 3.12  │  Pydantic Models  │  FIFO Engine │
├─────────────────────────────────────────────────┤
│                  Data Layer                       │
│  SQLAlchemy ORM  │  Alembic Migrations           │
├─────────────────────────────────────────────────┤
│                   Database                        │
│              SQLite (lokal)                       │
│        PostgreSQL (optional Cloud)                │
├─────────────────────────────────────────────────┤
│               External Services                   │
│  EZB-Kurse (CurrencyConverter)  │  ibflex Parser │
└─────────────────────────────────────────────────┘
2.2 Detaillierte Stack-Begründung
Komponente	Technologie	Begründung
Sprache	Python 3.12+	Pandas, beste Finance-Libs, AI-Agents können Python am besten
Datenbank	SQLite + SQLAlchemy	Lokal, kein Server nötig, portable .db-Datei, für Single-User perfekt
ORM	SQLAlchemy 2.0	Type-safe, Migrations via Alembic, Standard
Datenvalidierung	Pydantic v2	Strikte Typisierung, automatische Konvertierung, perfekt für Finanzdaten
IBKR-Parsing	ibflex + custom CSV-Parser	ibflex parst Flex Queries zuverlässig
Währung	CurrencyConverter	Offline-EZB-Kurse, kein API-Call pro Trade
Zahlen	decimal.Decimal	NIEMALS float für Geldbeträge!
UI	Streamlit	Schnellstes Prototyping, ausreichend für Steuerberater-Tool
Excel-Export	openpyxl	Formatierte Ausgabe, mehrere Sheets
Testing	pytest + pytest-cov	TDD, parametrisierte Tests
Dependency Mgmt	poetry oder uv	Reproduzierbare Builds
Linting	ruff	Schnellster Python-Linter
Dezimalrechnung	decimal (stdlib)	Exakte Berechnung, keine Rundungsfehler
2.3 Dependencies (pyproject.toml)
toml

[tool.poetry.dependencies]
python = "^3.12"
sqlalchemy = "^2.0"
alembic = "^1.13"
pydantic = "^2.5"
pandas = "^2.2"
ibflex = "^0.16"          # IBKR Flex Query Parser
CurrencyConverter = "^0.17"  # EZB-Kurse
openpyxl = "^3.1"         # Excel-Export
streamlit = "^1.40"       # UI
click = "^8.1"            # CLI (optional)

[tool.poetry.group.dev.dependencies]
pytest = "^8.0"
pytest-cov = "^5.0"
factory-boy = "^3.3"      # Test-Daten-Factories
ruff = "^0.8"
3. Datenbank-Schema (vollständig)
3.1 ER-Diagramm (konzeptionell)

┌──────────────┐     ┌──────────────────┐     ┌──────────────────┐
│   accounts   │────<│     trades       │────<│   fifo_lots      │
└──────────────┘     └──────────────────┘     └──────────────────┘
       │                     │                         │
       │              ┌──────┴──────┐                  │
       │              │             │                  │
       ▼              ▼             ▼                  ▼
┌──────────────┐ ┌──────────┐ ┌──────────────┐ ┌──────────────────┐
│  dividends   │ │  fees    │ │  interest    │ │ realized_gains   │
└──────────────┘ └──────────┘ └──────────────┘ └──────────────────┘
       │
       ▼
┌──────────────────┐
│ withholding_tax  │
└──────────────────┘

┌──────────────────┐     ┌──────────────────┐
│corporate_actions │     │  exchange_rates   │
└──────────────────┘     └──────────────────┘
3.2 Tabellen-Definitionen
Python

# models.py - SQLAlchemy Models

from sqlalchemy import (Column, Integer, String, Date, DateTime, 
                         Numeric, ForeignKey, Enum, Boolean, Text)
from sqlalchemy.orm import DeclarativeBase, relationship
import enum
from decimal import Decimal

class Base(DeclarativeBase):
    pass

class AssetCategory(enum.Enum):
    STOCK = "STK"                    # Aktien
    OPTION = "OPT"                   # Optionen
    FUTURE = "FUT"                   # Futures
    FOREX = "CASH"                   # Devisen
    BOND = "BOND"                    # Anleihen
    FUND = "FUND"                    # Fonds/ETFs
    WARRANT = "WAR"                  # Optionsscheine
    CFD = "CFD"

class TaxCategory(enum.Enum):
    """Deutsche steuerliche Kategorisierung"""
    AKTIENGEWINN = "aktien_gewinn"              # Zeile 9 KAP
    AKTIENVERLUST = "aktien_verlust"            # Zeile 10 KAP  
    TERMINGESCHAEFT = "termingeschaeft"         # Zeile 11/12 KAP
    DIVIDENDE = "dividende"                     # Zeile 8 KAP
    ZINSEN = "zinsen"                           # Zeile 8 KAP
    SONSTIGE_ERTRAEGE = "sonstige"              # Zeile 8 KAP
    QUELLENSTEUER = "quellensteuer"             # Zeile 15 KAP
    WAEHRUNGSGEWINN = "waehrungsgewinn"         # §23 EStG

class Account(Base):
    __tablename__ = "accounts"
    id = Column(Integer, primary_key=True)
    account_id = Column(String(20), unique=True, nullable=False)  # z.B. "U1234567"
    account_name = Column(String(100))
    base_currency = Column(String(3), default="EUR")
    created_at = Column(DateTime, server_default="CURRENT_TIMESTAMP")

class Trade(Base):
    __tablename__ = "trades"
    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    
    # IBKR-Identifikation
    trade_id = Column(String(50), unique=True)        # IBKR Trade ID
    ib_order_id = Column(String(50))
    
    # Zeitstempel
    trade_date = Column(DateTime, nullable=False)
    settle_date = Column(Date)                        # Wichtig für Steuerjahr!
    
    # Instrument
    asset_category = Column(Enum(AssetCategory), nullable=False)
    symbol = Column(String(50), nullable=False)
    description = Column(String(200))
    isin = Column(String(12))
    underlying_symbol = Column(String(20))            # Bei Optionen
    expiry = Column(Date)                             # Bei Optionen
    strike = Column(Numeric(precision=12, scale=4))   # Bei Optionen
    put_call = Column(String(1))                      # P oder C
    multiplier = Column(Integer, default=1)           # Bei Optionen: 100
    
    # Trade-Daten
    buy_sell = Column(String(4), nullable=False)      # BUY oder SELL
    quantity = Column(Numeric(precision=15, scale=6), nullable=False)
    price = Column(Numeric(precision=15, scale=6), nullable=False)
    currency = Column(String(3), nullable=False)
    
    # Beträge in Originalwährung
    proceeds = Column(Numeric(precision=15, scale=2))
    commission = Column(Numeric(precision=10, scale=2))
    tax = Column(Numeric(precision=10, scale=2), default=0)
    net_cash = Column(Numeric(precision=15, scale=2))
    
    # EUR-Umrechnung
    exchange_rate = Column(Numeric(precision=12, scale=6))  # EZB-Kurs am Trade-Tag
    proceeds_eur = Column(Numeric(precision=15, scale=2))
    commission_eur = Column(Numeric(precision=10, scale=2))
    net_cash_eur = Column(Numeric(precision=15, scale=2))
    
    # Flags
    open_close = Column(String(1))                    # O=Open, C=Close
    is_corporate_action = Column(Boolean, default=False)
    notes = Column(Text)

class FifoLot(Base):
    """Ein offener FIFO-Posten (noch nicht verkauft)"""
    __tablename__ = "fifo_lots"
    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    buy_trade_id = Column(Integer, ForeignKey("trades.id"), nullable=False)
    
    symbol = Column(String(50), nullable=False)
    asset_category = Column(Enum(AssetCategory), nullable=False)
    buy_date = Column(Date, nullable=False)
    
    original_quantity = Column(Numeric(precision=15, scale=6), nullable=False)
    remaining_quantity = Column(Numeric(precision=15, scale=6), nullable=False)
    
    cost_per_unit = Column(Numeric(precision=15, scale=6), nullable=False)       # Originalwährung
    cost_per_unit_eur = Column(Numeric(precision=15, scale=6), nullable=False)   # EUR
    commission_per_unit = Column(Numeric(precision=10, scale=6))                 # Anteilige Kommission
    commission_per_unit_eur = Column(Numeric(precision=10, scale=6))
    currency = Column(String(3), nullable=False)

class RealizedGain(Base):
    """Ein realisierter Gewinn/Verlust (für die Steuer)"""
    __tablename__ = "realized_gains"
    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    sell_trade_id = Column(Integer, ForeignKey("trades.id"), nullable=False)
    fifo_lot_id = Column(Integer, ForeignKey("fifo_lots.id"), nullable=False)
    
    tax_year = Column(Integer, nullable=False)         # Steuerjahr (basierend auf Settle-Date)
    asset_category = Column(Enum(AssetCategory), nullable=False)
    tax_category = Column(Enum(TaxCategory), nullable=False)
    
    symbol = Column(String(50), nullable=False)
    
    # Zeiträume
    buy_date = Column(Date, nullable=False)
    sell_date = Column(Date, nullable=False)
    settle_date = Column(Date, nullable=False)
    holding_period_days = Column(Integer)
    
    # Mengen
    quantity = Column(Numeric(precision=15, scale=6), nullable=False)
    
    # Beträge in EUR
    cost_basis_eur = Column(Numeric(precision=15, scale=2), nullable=False)     # Anschaffungskosten
    proceeds_eur = Column(Numeric(precision=15, scale=2), nullable=False)       # Veräußerungserlös
    buy_commission_eur = Column(Numeric(precision=10, scale=2))                 # Kaufgebühren
    sell_commission_eur = Column(Numeric(precision=10, scale=2))                # Verkaufsgebühren
    gain_loss_eur = Column(Numeric(precision=15, scale=2), nullable=False)      # Gewinn/Verlust

class Dividend(Base):
    __tablename__ = "dividends"
    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    date = Column(Date, nullable=False)
    pay_date = Column(Date)
    ex_date = Column(Date)
    symbol = Column(String(50), nullable=False)
    isin = Column(String(12))
    description = Column(String(200))
    amount = Column(Numeric(precision=15, scale=2), nullable=False)
    currency = Column(String(3), nullable=False)
    exchange_rate = Column(Numeric(precision=12, scale=6))
    amount_eur = Column(Numeric(precision=15, scale=2))
    tax_year = Column(Integer)

class WithholdingTax(Base):
    __tablename__ = "withholding_taxes"
    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    date = Column(Date, nullable=False)
    symbol = Column(String(50), nullable=False)
    description = Column(String(200))
    amount = Column(Numeric(precision=15, scale=2), nullable=False)  # Negativ!
    currency = Column(String(3), nullable=False)
    exchange_rate = Column(Numeric(precision=12, scale=6))
    amount_eur = Column(Numeric(precision=15, scale=2))
    tax_year = Column(Integer)
    # DBA-Anrechnungslimit
    country = Column(String(2))                      # Länderkürzel
    max_creditable_rate = Column(Numeric(precision=5, scale=4))  # z.B. 0.15 für USA

class Interest(Base):
    __tablename__ = "interest"
    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    date = Column(Date, nullable=False)
    description = Column(String(200))
    amount = Column(Numeric(precision=15, scale=2), nullable=False)
    currency = Column(String(3), nullable=False)
    exchange_rate = Column(Numeric(precision=12, scale=6))
    amount_eur = Column(Numeric(precision=15, scale=2))
    tax_year = Column(Integer)

class CorporateAction(Base):
    __tablename__ = "corporate_actions"
    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    date = Column(Date, nullable=False)
    action_type = Column(String(20))                  # SPLIT, MERGER, SPINOFF, etc.
    symbol = Column(String(50), nullable=False)
    description = Column(String(300))
    quantity = Column(Numeric(precision=15, scale=6))
    value = Column(Numeric(precision=15, scale=2))
    currency = Column(String(3))
    ratio = Column(String(20))                        # z.B. "4:1" bei Split
    processed = Column(Boolean, default=False)

class ExchangeRate(Base):
    """Cache für EZB-Kurse"""
    __tablename__ = "exchange_rates"
    id = Column(Integer, primary_key=True)
    date = Column(Date, nullable=False)
    currency = Column(String(3), nullable=False)
    rate_to_eur = Column(Numeric(precision=12, scale=6), nullable=False)
4. Vollständige Feature-Matrix
4.1 Steuerrechtliche Anforderungen (Deutschland)
#	Feature	Priorität	Steuerliche Grundlage	Komplexität
1	FIFO-Berechnung pro Symbol	KRITISCH	§20 Abs. 4 Satz 7 EStG	Hoch
2	Trennung Aktien vs. Termingeschäfte	KRITISCH	§20 Abs. 6 Satz 4 + 5 EStG	Mittel
3	Aktien-Verlusttopf (separater Verrechnungskreis)	KRITISCH	§20 Abs. 6 Satz 4 EStG	Mittel
4	Termingeschäfte voll verrechenbar (seit JStG 2024)	KRITISCH	JStG 2024, §20 Abs. 6 Satz 5 aufgehoben	Niedrig
5	EZB-Tageskurse für Währungsumrechnung	KRITISCH	BMF-Schreiben, EStR	Mittel
6	Dividenden-Erfassung	HOCH	§20 Abs. 1 Nr. 1 EStG	Niedrig
7	Quellensteuer-Anrechnung	HOCH	§34c EStG + DBA	Mittel
8	Zinsen (IBKR-Kontozinsen)	HOCH	§20 Abs. 1 Nr. 7 EStG	Niedrig
9	Options-Verfall (wertloser Verfall)	HOCH	BFH VIII R 3/21	Mittel
10	Options-Ausübung/-Zuweisung	HOCH	BMF-Schreiben	Hoch
11	Corporate Actions (Splits)	MITTEL	Anpassung Anschaffungskosten	Hoch
12	Währungsgewinne (§23 EStG)	MITTEL	§23 Abs. 1 Nr. 2 EStG	Sehr hoch
13	Vorabpauschale (ETFs)	NIEDRIG	§18 InvStG	Hoch
14	Teilfreistellung (Fonds)	NIEDRIG	§20 InvStG	Mittel
4.2 Verlustverrechnungstöpfe (vereinfacht)

┌─────────────────────────────────────────────────┐
│          TOPF 1: Aktienverrechnungstopf          │
│  Nur Verluste aus Aktienveräußerungen            │
│  → Nur verrechenbar mit Aktiengewinnen           │
│  → Nicht mit Dividenden, Optionen, etc.          │
│  → Unbegrenzt vortragbar                         │
├─────────────────────────────────────────────────┤
│          TOPF 2: Allgemeiner Topf                │
│  Dividenden, Zinsen, Optionsgewinne/-verluste,   │
│  sonstige Kapitalerträge                         │
│  → Untereinander frei verrechenbar               │
│  → Seit JStG 2024: Keine 20k-Grenze mehr!       │
└─────────────────────────────────────────────────┘
5. Software-Architektur
5.1 Modulstruktur

ibkr-tax-tool/
├── pyproject.toml
├── README.md
├── alembic/                          # DB-Migrationen
│   ├── alembic.ini
│   └── versions/
├── src/
│   └── ibkr_tax/
│       ├── __init__.py
│       ├── config.py                 # Settings (DB-Pfad, Steuerjahr, etc.)
│       │
│       ├── models/                   # Pydantic + SQLAlchemy Models
│       │   ├── __init__.py
│       │   ├── database.py           # SQLAlchemy Models (wie oben)
│       │   └── schemas.py            # Pydantic Schemas für Validierung
│       │
│       ├── db/                       # Datenbankzugriff
│       │   ├── __init__.py
│       │   ├── engine.py             # DB-Engine + Session
│       │   └── repository.py         # CRUD-Operationen
│       │
│       ├── parsers/                  # Daten-Import
│       │   ├── __init__.py
│       │   ├── flex_parser.py        # Flex Query XML (primär)
│       │   ├── csv_parser.py         # Activity Statement CSV (Fallback)
│       │   └── data_cleaner.py       # Normalisierung, Deduplizierung
│       │
│       ├── fx/                       # Währungsumrechnung
│       │   ├── __init__.py
│       │   └── ecb_rates.py          # EZB-Kurse via CurrencyConverter
│       │
│       ├── engine/                   # Steuerberechnung
│       │   ├── __init__.py
│       │   ├── fifo.py               # FIFO-Engine
│       │   ├── tax_categorizer.py    # Steuerliche Zuordnung
│       │   ├── corporate_actions.py  # Splits, Mergers
│       │   └── options_handler.py    # Verfall, Ausübung, Assignment
│       │
│       ├── reports/                  # Export
│       │   ├── __init__.py
│       │   ├── excel_export.py       # Excel für Steuerberater
│       │   ├── summary.py            # Zusammenfassung für Anlage KAP
│       │   └── templates/            # Excel-Vorlagen
│       │
│       └── ui/                       # Streamlit-App
│           ├── app.py                # Hauptapp
│           ├── pages/
│           │   ├── 01_import.py
│           │   ├── 02_overview.py
│           │   ├── 03_trades.py
│           │   ├── 04_dividends.py
│           │   └── 05_export.py
│           └── components/
│
├── tests/                            # TDD!
│   ├── conftest.py                   # Fixtures, Test-DB
│   ├── fixtures/                     # Test-Dateien
│   │   ├── sample_flex_query.xml
│   │   ├── sample_activity.csv
│   │   └── expected_results.json
│   ├── test_parsers/
│   │   ├── test_flex_parser.py
│   │   └── test_csv_parser.py
│   ├── test_fx/
│   │   └── test_ecb_rates.py
│   ├── test_engine/
│   │   ├── test_fifo.py
│   │   ├── test_fifo_edge_cases.py
│   │   ├── test_tax_categorizer.py
│   │   └── test_options.py
│   ├── test_reports/
│   │   └── test_excel_export.py
│   └── test_integration/
│       └── test_full_pipeline.py
│
└── scripts/
    └── generate_test_data.py         # Generiert realistische Testdaten
6. Entwicklungsplan – 14 Phasen (TDD, sehr granular)
Jede Phase hat:

Ziel: Was wird gebaut?
Tests zuerst: Welche Tests schreiben wir?
Prompt: Exakter Prompt für den AI-Agenten
Validierung: Wie prüfen wir, ob es funktioniert?

Phase 0: Projekt-Setup
Ziel: Leeres Projekt mit allen Dependencies, DB-Engine, ein "Hello World"-Test geht durch.


PROMPT FÜR AI-AGENT:

Erstelle ein Python-Projekt mit folgender Struktur:

1. Nutze `poetry` für Dependency-Management.
2. Installiere: sqlalchemy>=2.0, alembic, pydantic>=2.5, pandas, pytest, pytest-cov, ruff
3. Erstelle die Ordnerstruktur:
   - src/ibkr_tax/ (mit __init__.py)
   - src/ibkr_tax/models/
   - src/ibkr_tax/db/
   - tests/ (mit conftest.py)
4. In src/ibkr_tax/db/engine.py:
   - Erstelle eine Funktion `get_engine(db_url: str = "sqlite:///ibkr_tax.db")` die ein SQLAlchemy engine zurückgibt
   - Erstelle eine Funktion `get_session()` die eine Session zurückgibt (sessionmaker)
   - Erstelle eine Funktion `init_db(engine)` die `Base.metadata.create_all(engine)` aufruft
5. In tests/conftest.py:
   - Erstelle eine pytest-Fixture `db_engine` die eine In-Memory SQLite DB nutzt: `sqlite:///:memory:`
   - Erstelle eine Fixture `db_session` die eine Session gibt und nach dem Test alles rollbackt
6. In tests/test_db_setup.py:
   - Schreibe einen Test der prüft, dass die Engine erstellt werden kann
   - Schreibe einen Test der prüft, dass `init_db` keine Fehler wirft

Nutze KEIN float für Geldbeträge, sondern immer `decimal.Decimal` bzw. `Numeric` in SQLAlchemy.
Alle Dateien sollen type hints nutzen.
Validierung: pytest tests/test_db_setup.py -v → 2 Tests grün.

Phase 1: Datenbank-Models
Ziel: Alle SQLAlchemy-Models erstellt, Tabellen werden angelegt, einfache CRUD-Tests.


PROMPT FÜR AI-AGENT:

Erstelle die SQLAlchemy 2.0 Models in src/ibkr_tax/models/database.py.
Nutze den DeclarativeBase-Stil (nicht den Legacy-Stil).

Erstelle folgende Models mit exakt diesen Feldern:

1. Account:
   - id: Integer, Primary Key
   - account_id: String(20), unique, not null (z.B. "U1234567")
   - account_name: String(100), nullable
   - base_currency: String(3), default "EUR"

2. Trade:
   - id: Integer, Primary Key
   - account_id: ForeignKey("accounts.id"), not null
   - trade_id: String(50), unique (IBKR Trade-ID)
   - trade_date: DateTime, not null
   - settle_date: Date (Abrechnungsdatum, entscheidet über Steuerjahr!)
   - asset_category: String(10), not null (Werte: "STK", "OPT", "FUT", "CASH", "BOND", "FUND")
   - symbol: String(50), not null
   - description: String(200)
   - isin: String(12), nullable
   - underlying_symbol: String(20), nullable (bei Optionen)
   - expiry: Date, nullable (bei Optionen)
   - strike: Numeric(12,4), nullable (bei Optionen)
   - put_call: String(1), nullable (P oder C)
   - multiplier: Integer, default 1 (bei Optionen: 100)
   - buy_sell: String(4), not null (BUY oder SELL)
   - quantity: Numeric(15,6), not null
   - price: Numeric(15,6), not null
   - currency: String(3), not null
   - proceeds: Numeric(15,2)
   - commission: Numeric(10,2)
   - net_cash: Numeric(15,2)
   - exchange_rate: Numeric(12,6), nullable (EZB-Kurs)
   - proceeds_eur: Numeric(15,2), nullable
   - commission_eur: Numeric(10,2), nullable
   - net_cash_eur: Numeric(15,2), nullable
   - open_close: String(1), nullable (O oder C)
   - notes: Text, nullable

3. FifoLot:
   - id: Integer, Primary Key
   - account_id: ForeignKey, not null
   - buy_trade_id: ForeignKey("trades.id"), not null
   - symbol: String(50), not null
   - asset_category: String(10), not null
   - buy_date: Date, not null
   - original_quantity: Numeric(15,6), not null
   - remaining_quantity: Numeric(15,6), not null
   - cost_per_unit_eur: Numeric(15,6), not null
   - commission_per_unit_eur: Numeric(10,6), nullable
   - currency: String(3), not null

4. RealizedGain:
   - id: Integer, Primary Key
   - account_id: ForeignKey, not null
   - sell_trade_id: ForeignKey("trades.id"), not null
   - fifo_lot_id: ForeignKey("fifo_lots.id"), not null
   - tax_year: Integer, not null
   - asset_category: String(10), not null
   - tax_category: String(30), not null (Werte: "aktien_gewinn", "aktien_verlust", "termingeschaeft", "sonstige")
   - symbol: String(50), not null
   - buy_date: Date, not null
   - sell_date: Date, not null
   - settle_date: Date, not null
   - holding_period_days: Integer
   - quantity: Numeric(15,6), not null
   - cost_basis_eur: Numeric(15,2), not null
   - proceeds_eur: Numeric(15,2), not null
   - buy_commission_eur: Numeric(10,2)
   - sell_commission_eur: Numeric(10,2)
   - gain_loss_eur: Numeric(15,2), not null

5. Dividend:
   - id, account_id, date, symbol, isin, description, amount, currency, exchange_rate, amount_eur, tax_year

6. WithholdingTax:
   - id, account_id, date, symbol, description, amount (negativ!), currency, exchange_rate, amount_eur, tax_year, country (2-stellig)

7. Interest:
   - id, account_id, date, description, amount, currency, exchange_rate, amount_eur, tax_year

8. CorporateAction:
   - id, account_id, date, action_type, symbol, description, quantity, value, currency, processed (Boolean)

9. ExchangeRate (Cache):
   - id, date, currency, rate_to_eur (Numeric(12,6))
   - Unique constraint auf (date, currency)

WICHTIG: 
- Nutze `from decimal import Decimal`
- Alle Geldbeträge als Numeric, NIEMALS als Float
- Erstelle eine Relationship von Account zu Trades, Dividends, etc.

Schreibe außerdem Tests in tests/test_models.py:
- Test: Alle Tabellen werden in einer leeren DB angelegt (create_all)
- Test: Ein Account kann erstellt und wieder gelesen werden
- Test: Ein Trade kann erstellt werden mit Fremdschlüssel zum Account
- Test: Ein RealizedGain kann erstellt werden mit Fremdschlüsseln

Jeder Test soll die In-Memory-DB aus conftest.py nutzen.
Validierung: pytest tests/test_models.py -v → alle Tests grün.

Phase 2: Pydantic-Schemas für Datenvalidierung
Ziel: Streng typisierte Eingabe-Schemas, die die rohen IBKR-Daten validieren, bevor sie in die DB geschrieben werden.


PROMPT FÜR AI-AGENT:

Erstelle Pydantic v2 Schemas in src/ibkr_tax/models/schemas.py.

Diese Schemas dienen als Validierungsschicht zwischen dem Parser und der Datenbank.
Sie stellen sicher, dass alle Pflichtfelder vorhanden sind und die richtigen Typen haben.

1. TradeSchema(BaseModel):
   - trade_id: str
   - trade_date: datetime
   - settle_date: date | None = None
   - asset_category: Literal["STK", "OPT", "FUT", "CASH", "BOND", "FUND"]
   - symbol: str (min_length=1)
   - description: str = ""
   - isin: str | None = None (Pattern: r"^[A-Z]{2}[A-Z0-9]{10}$" wenn vorhanden)
   - buy_sell: Literal["BUY", "SELL"]
   - quantity: Decimal (muss > 0 sein)
   - price: Decimal
   - currency: str (length=3)
   - proceeds: Decimal
   - commission: Decimal
   - net_cash: Decimal
   - multiplier: int = 1
   
   Validators:
   - Bei BUY muss proceeds negativ sein (Geld geht raus), bei SELL positiv
   - commission ist typischerweise negativ (Kosten)
   - Wenn asset_category == "OPT", dann muss multiplier gesetzt sein (default 100)

   model_config: ConfigDict mit coerce_numbers_to_str=False, arbitrary_types_allowed=True

2. DividendSchema(BaseModel):
   - date: date
   - symbol: str
   - description: str
   - amount: Decimal (positiv für Ausschüttung)
   - currency: str

3. WithholdingTaxSchema(BaseModel):
   - date: date
   - symbol: str
   - description: str
   - amount: Decimal (typischerweise negativ)
   - currency: str

4. InterestSchema(BaseModel):
   - date: date
   - description: str
   - amount: Decimal
   - currency: str

Schreibe Tests in tests/test_schemas.py:
- Test: Gültiger Trade wird akzeptiert (STK, BUY, USD)
- Test: Trade ohne symbol wird rejected (ValidationError)
- Test: Trade mit ungültiger asset_category wird rejected
- Test: Dividend mit positivem Betrag wird akzeptiert
- Test: WithholdingTax mit negativem Betrag wird akzeptiert
- Test: Trade mit ISIN die nicht dem Pattern entspricht wird rejected
- Nutze pytest.raises(ValidationError) für die Negativtests
Validierung: pytest tests/test_schemas.py -v

Phase 3: EZB-Wechselkurse
Ziel: Zuverlässige Währungsumrechnung mit EZB-Tageskursen, Wochenend-Fallback.


PROMPT FÜR AI-AGENT:

Erstelle das Modul src/ibkr_tax/fx/ecb_rates.py für die Währungsumrechnung.

Anforderungen:
- Das deutsche Finanzamt verlangt die offiziellen EZB-Referenzkurse
- An Wochenenden und Feiertagen gibt es keine EZB-Kurse → letzten verfügbaren Kurs nutzen
- EUR-Trades brauchen keine Umrechnung (Rate = 1.0)

Implementierung:

1. Klasse EcbRateProvider:
   
   __init__(self):
     - Initialisiert CurrencyConverter aus der Bibliothek 'CurrencyConverter' (pip install CurrencyConverter)
     - Nutze: `self.cc = CurrencyConverter(fallback_on_wrong_date=True, fallback_on_missing_rate=True)`
     - Das lädt automatisch die historischen EZB-Kurse herunter
   
   get_rate(self, currency: str, date: date) -> Decimal:
     - Wenn currency == "EUR": return Decimal("1.0")
     - Sonst: Nutze self.cc.convert(1, currency, 'EUR', date=date) und konvertiere zu Decimal
     - Runde auf 6 Nachkommastellen
     - Fange Exceptions ab (RateNotFoundError) und versuche die vorherigen Tage (maximal 5 Tage zurück)
   
   convert_to_eur(self, amount: Decimal, currency: str, date: date) -> Decimal:
     - Multipliziert amount mit get_rate()
     - Rundet auf 2 Nachkommastellen (kaufmännische Rundung)
   
   get_rate_cached(self, currency: str, date: date, session: Session) -> Decimal:
     - Prüft zuerst die ExchangeRate-Tabelle in der DB
     - Wenn nicht vorhanden: holt den Kurs via get_rate() und speichert ihn in der DB
     - Gibt den Kurs zurück

2. Schreibe Tests in tests/test_fx/test_ecb_rates.py:
   - Test: EUR zu EUR gibt Rate 1.0 zurück
   - Test: USD zu EUR an einem Werktag (z.B. 2024-06-03) gibt einen sinnvollen Kurs (zwischen 0.85 und 0.99)
   - Test: GBP zu EUR an einem Werktag gibt einen sinnvollen Kurs
   - Test: Wochenende (z.B. 2024-06-01, Samstag) gibt den Freitagskurs zurück
   - Test: convert_to_eur rechnet 100 USD korrekt um (100 * rate, gerundet auf 2 Stellen)
   - Test: convert_to_eur mit EUR gibt den Originalbetrag zurück
   - Test: Caching in DB funktioniert (zweiter Aufruf liest aus DB statt API)

HINWEIS: Die CurrencyConverter-Bibliothek braucht bei der ersten Nutzung einen Internet-Download.
In Tests können wir die echte Bibliothek nutzen (die Daten sind offline gecacht nach dem ersten Load).
Validierung: pytest tests/test_fx/ -v

Phase 4: IBKR Flex Query XML Parser
Ziel: Flex Query XML-Dateien einlesen und als validierte Pydantic-Objekte zurückgeben.


PROMPT FÜR AI-AGENT:

Installiere die Bibliothek `ibflex` (pip install ibflex).
Erstelle den Parser in src/ibkr_tax/parsers/flex_parser.py.

Die ibflex-Bibliothek parst IBKR Flex Query XML-Reports. Die Verwendung ist:

```python
from ibflex import parser, Types
report = parser.parse("report.xml")  # Gibt ein FlexQueryResponse zurück
for statement in report.FlexStatements:
    account_id = statement.accountId
    for trade in statement.Trades:
        # trade.symbol, trade.dateTime, trade.quantity, trade.tradePrice, etc.
Implementiere die Klasse FlexQueryParser:

class FlexQueryParser:


def parse_file(self, file_path: str | Path) -> ParseResult:
    """Parst eine Flex Query XML-Datei und gibt strukturierte Daten zurück"""
    
def _parse_trades(self, trades: list) -> list[TradeSchema]:
    """Konvertiert ibflex Trade-Objekte zu unseren TradeSchema-Objekten"""
    - Mappe assetCategory: "STK" -> "STK", "OPT" -> "OPT", etc.
    - Mappe buySell: "BUY" -> "BUY", "SELL" -> "SELL"  
      ACHTUNG: IBKR hat auch "BUY (Ca.)" für Corporate Actions!
    - quantity: Immer als positiven Wert speichern (IBKR gibt bei SELL manchmal negativ)
    - commission: Ist bei IBKR negativ (Kosten), so beibehalten
    - Berechne net_cash = proceeds + commission
    - Bei Optionen: multiplier aus trade.multiplier, 
      underlying aus trade.underlyingSymbol, 
      expiry/strike/putCall aus dem Optionssymbol
    
def _parse_dividends(self, dividends: list) -> list[DividendSchema]:
    """Konvertiert Dividenden"""
    
def _parse_withholding_tax(self, taxes: list) -> list[WithholdingTaxSchema]:
    """Konvertiert Quellensteuern"""
    - Extrahiere das Land aus der Description (z.B. "US Tax" -> country="US")
    
def _parse_interest(self, interest: list) -> list[InterestSchema]:
    """Konvertiert Zinsen"""

def _parse_corporate_actions(self, actions: list) -> list[CorporateActionSchema]:
    """Konvertiert Corporate Actions (Splits, etc.)"""
@dataclass
class ParseResult:
account_id: str
trades: list[TradeSchema]
dividends: list[DividendSchema]
withholding_taxes: list[WithholdingTaxSchema]
interest: list[InterestSchema]
corporate_actions: list[CorporateActionSchema]
errors: list[str] # Zeilen die nicht geparst werden konnten

Für die Tests erstelle eine Testdatei tests/fixtures/sample_flex.xml mit folgendem Inhalt:
(Erstelle ein minimales aber valides Flex Query XML mit:

2 Aktien-Käufe (AAPL, MSFT in USD)
1 Aktien-Verkauf (AAPL in USD)
1 Options-Trade (SPY Put)
1 Dividende (AAPL)
1 Quellensteuer (AAPL)
1 Zinseinnahme
Nutze realistische Werte und Daten aus 2023/2024)
Tests in tests/test_parsers/test_flex_parser.py:

Test: XML wird ohne Fehler geparst
Test: Korrekte Anzahl Trades wird extrahiert
Test: Aktien-Trade hat korrekte Felder (symbol, quantity, price, etc.)
Test: Options-Trade hat multiplier=100 und underlying gesetzt
Test: Dividende hat korrekten Betrag und Symbol
Test: Quellensteuer ist negativ
Test: Ungültige XML-Datei wirft eine sinnvolle Exception


**Validierung**: `pytest tests/test_parsers/test_flex_parser.py -v`

---

### Phase 5: IBKR CSV Activity Statement Parser (Fallback)

**Ziel**: CSV-Parser für den Fall, dass Nutzer kein Flex Query haben.
PROMPT FÜR AI-AGENT:

Erstelle den CSV-Parser in src/ibkr_tax/parsers/csv_parser.py.

IBKR Activity Statement CSVs haben ein besonderes Format:

Jede Zeile beginnt mit dem Sektionsnamen
Danach kommt "Header" (Spaltennamen) oder "Data" (Werte) oder "SubTotal"/"Total"
Die Spalten sind je nach Sektion unterschiedlich
Beispiel:


Trades,Header,DataDiscriminator,Asset Category,Currency,Symbol,Date/Time,Quantity,T. Price,Proceeds,Comm/Fee,Code
Trades,Data,Order,Stocks,USD,AAPL,"2024-03-15, 10:30:00",100,175.50,17550.00,-1.00,O
Trades,Data,Order,Stocks,USD,AAPL,"2024-08-20, 14:15:00",-100,225.00,-22500.00,-1.00,C
Trades,SubTotal,,Stocks,USD,,,,,,-2.00,
Trades,Data,Order,Equity and Index Options,USD,SPY 240315P00500000,"2024-02-01, 09:45:00",-5,3.50,-1750.00,-5.25,O
...
Dividends,Header,Currency,Date,Description,Amount
Dividends,Data,USD,2024-06-15,"AAPL(US0378331005) Cash Dividend 0.25000000 USD per Share (Ordinary Dividend)",25.00
Dividends,Total,,,Total,125.50
...
Withholding Tax,Header,Currency,Date,Description,Amount
Withholding Tax,Data,USD,2024-06-15,"AAPL(US0378331005) Cash Dividend 0.25000000 USD per Share - US Tax",-3.75
Implementiere die Klasse CsvActivityParser:

class CsvActivityParser:


def parse_file(self, file_path: str | Path) -> ParseResult:
    """Parst ein IBKR Activity Statement CSV"""
    1. Lies die gesamte Datei ein
    2. Gruppiere Zeilen nach Sektionsname (erstes Feld)
    3. Für jede Sektion: Finde die "Header"-Zeile und nutze sie als Spaltennamen
    4. Filtere "Data"-Zeilen (ignoriere "SubTotal", "Total", "Header")
    5. Parse jede Sektion separat

def _extract_section(self, lines: list[str], section_name: str) -> pd.DataFrame:
    """Extrahiert eine Section als DataFrame"""
    - Finde die Header-Zeile: `section_name,Header,...`
    - Finde alle Data-Zeilen: `section_name,Data,...`
    - Erstelle einen DataFrame mit den Header-Spalten
    - ACHTUNG: Ignoriere "SubTotal" und "Total" Zeilen!
    
def _parse_trades_section(self, df: pd.DataFrame) -> list[TradeSchema]:
    """Parst die Trades-Section"""
    - Asset Category "Stocks" -> "STK"
    - Asset Category "Equity and Index Options" -> "OPT"
    - Asset Category "Futures" -> "FUT"
    - Asset Category "Forex" -> "CASH"
    - Negative Quantity = SELL, positive = BUY
    - Date/Time Format: "2024-03-15, 10:30:00" (mit Komma!)
      Nutze strptime mit passendem Format
    - DataDiscriminator muss "Order" oder "Trade" sein (ignoriere "ClosedLot" etc.)
    
def _parse_dividends_section(self, df: pd.DataFrame) -> list[DividendSchema]:

def _parse_withholding_section(self, df: pd.DataFrame) -> list[WithholdingTaxSchema]:
    - Extrahiere ISIN aus Description: Regex r'\(([A-Z]{2}[A-Z0-9]{10})\)'
    - Extrahiere Land aus Description: "US Tax" -> "US", "CA Tax" -> "CA"

def _parse_interest_section(self, df: pd.DataFrame) -> list[InterestSchema]:
WICHTIG beim CSV-Parsing:

Nutze csv.reader statt pandas.read_csv für das initiale Einlesen,
da die Sektionen unterschiedliche Spaltenanzahlen haben
Manche Felder enthalten Kommas in Anführungszeichen (z.B. Descriptions)
Das Encoding ist typischerweise UTF-8 mit BOM (utf-8-sig)
Erstelle eine Test-CSV-Datei in tests/fixtures/sample_activity.csv mit realistischen Daten.

Tests in tests/test_parsers/test_csv_parser.py:

Test: CSV wird ohne Fehler geparst
Test: SubTotal- und Total-Zeilen werden ignoriert
Test: Trades werden korrekt extrahiert (Anzahl, Felder)
Test: Negative Quantity wird als SELL erkannt
Test: Datum mit Komma wird korrekt geparst
Test: Dividenden werden korrekt extrahiert
Test: Quellensteuer wird korrekt extrahiert
Test: ISIN wird aus Description extrahiert


**Validierung**: `pytest tests/test_parsers/test_csv_parser.py -v`

---

### Phase 6: Daten-Import-Pipeline (Parser → DB)

**Ziel**: Geparste Daten in die Datenbank schreiben, mit Deduplizierung.
PROMPT FÜR AI-AGENT:

Erstelle src/ibkr_tax/db/repository.py mit den CRUD-Operationen und
src/ibkr_tax/parsers/data_cleaner.py für die Datenbereinigung.

DataCleaner Klasse:

def deduplicate_trades(self, trades: list[TradeSchema]) -> list[TradeSchema]:
"""Entfernt Duplikate basierend auf trade_id"""

def normalize_symbols(self, trades: list[TradeSchema]) -> list[TradeSchema]:
"""Normalisiert Optionssymbole
IBKR verwendet: 'SPY 240315P00500000'
Wir extrahieren: underlying='SPY', expiry=2024-03-15, strike=500.00, put_call='P'
"""

def validate_consistency(self, result: ParseResult) -> list[str]:
"""Prüft auf Inkonsistenzen:
- Dividende ohne passenden Trade (Warnung)
- Quellensteuer ohne passende Dividende (Warnung)
- Verkäufe ohne vorherigen Kauf (Fehler!)
"""

TradeRepository Klasse:

def init(self, session: Session):

def get_or_create_account(self, account_id: str) -> Account:
"""Erstellt Account falls nicht vorhanden, sonst gibt existierenden zurück"""

def import_trades(self, account: Account, trades: list[TradeSchema], fx_provider: EcbRateProvider) -> ImportResult:
"""Importiert Trades in die DB
- Prüft auf Duplikate (trade_id already exists -> skip)
- Rechnet alle Beträge in EUR um via fx_provider
- Gibt ImportResult zurück (imported: int, skipped: int, errors: list)
"""

def import_dividends(self, account: Account, dividends: list[DividendSchema], fx_provider: EcbRateProvider) -> ImportResult:

def import_withholding_taxes(self, ...)

def import_interest(self, ...)

def get_all_trades_sorted(self, account: Account) -> list[Trade]:
"""Gibt alle Trades chronologisch sortiert zurück (für FIFO)"""

def get_trades_by_symbol(self, account: Account, symbol: str) -> list[Trade]:

@dataclass
class ImportResult:
imported: int
skipped: int # Duplikate
errors: list[str]

ImportService (Orchestrierung):

class ImportService:
def init(self, session: Session, fx_provider: EcbRateProvider):


def import_flex_query(self, file_path: str) -> ImportResult:
    """Kompletter Import-Workflow:
    1. Parse XML
    2. Validate & Clean
    3. Import to DB (mit EUR-Umrechnung)
    4. Gib Zusammenfassung zurück
    """

def import_csv_activity(self, file_path: str) -> ImportResult:
    """Wie oben, aber für CSV"""
Tests in tests/test_import_pipeline.py:

Test: Import einer Flex Query XML erzeugt korrekte DB-Einträge
Test: Doppelter Import derselben Datei erzeugt keine Duplikate
Test: EUR-Umrechnung wird bei USD-Trades durchgeführt
Test: EUR-Trades bekommen exchange_rate = 1.0
Test: ImportResult zeigt korrekte Zähler


**Validierung**: `pytest tests/test_import_pipeline.py -v`

---

### Phase 7: FIFO-Engine (Kernstück!)

**Ziel**: Die FIFO-Berechnung – das Herzstück der Anwendung.
PROMPT FÜR AI-AGENT:

Erstelle die FIFO-Engine in src/ibkr_tax/engine/fifo.py.
Dies ist das WICHTIGSTE Modul der gesamten Anwendung!

Das deutsche Steuerrecht verlangt FIFO (First-In-First-Out) bei der Zuordnung
von Verkäufen zu Käufen. Pro Symbol wird ein separater FIFO-Stack geführt.

WICHTIG: Alle Berechnungen in EUR (bereits beim Import umgerechnet)!
WICHTIG: Nutze überall decimal.Decimal für exakte Rechnung!

class FifoEngine:


def __init__(self):
    # Dict von symbol -> list of FifoLotRecord (FIFO-Stack)
    self.stacks: dict[str, list[FifoLotRecord]] = defaultdict(list)

def process_trades(self, trades: list[Trade], tax_year: int) -> FifoResult:
    """
    Verarbeitet ALLE Trades chronologisch (auch aus Vorjahren!) 
    und gibt nur die realisierten Gewinne des gewählten Steuerjahres zurück.
    
    Algorithmus:
    1. Sortiere alle Trades nach trade_date aufsteigend
    2. Für jeden Trade:
       a) Wenn BUY: Erstelle einen FifoLotRecord und pushe ihn auf den Stack für das Symbol
       b) Wenn SELL: 
          - Entnehme Lots vom ANFANG des Stacks (FIFO = ältester zuerst!)
          - Berechne Gewinn/Verlust pro Lot
          - Wenn das settle_date des Verkaufs im tax_year liegt: 
            speichere als RealizedGainRecord
          - Wenn der Stack leer ist, bevor die gesamte Verkaufsmenge abgearbeitet ist:
            → FEHLER: Short-Selling ohne vorherigen Kauf (sollte geloggt werden)
    """

def _process_buy(self, trade: Trade):
    """Fügt ein neues Lot zum FIFO-Stack hinzu"""
    lot = FifoLotRecord(
        trade_id=trade.id,
        symbol=trade.symbol,
        buy_date=trade.trade_date.date(),
        quantity=abs(trade.quantity),
        cost_per_unit_eur=abs(trade.proceeds_eur) / abs(trade.quantity),
        commission_per_unit_eur=abs(trade.commission_eur) / abs(trade.quantity),
        asset_category=trade.asset_category
    )
    self.stacks[trade.symbol].append(lot)

def _process_sell(self, trade: Trade, tax_year: int) -> list[RealizedGainRecord]:
    """
    FIFO-Verkaufslogik:
    
    remaining_qty = abs(trade.quantity)
    sell_price_per_unit_eur = abs(trade.proceeds_eur) / abs(trade.quantity)
    sell_commission_per_unit_eur = abs(trade.commission_eur) / abs(trade.quantity)
    
    results = []
    while remaining_qty > 0:
        if stack is empty:
            log error "No FIFO lots available for {symbol}"
            break
        
        oldest_lot = stack[0]
        
        if oldest_lot.quantity <= remaining_qty:
            # Gesamtes Lot wird verbraucht
            matched_qty = oldest_lot.quantity
            stack.pop(0)  # Lot ist aufgebraucht
        else:
            # Teilverkauf: Lot wird nur teilweise verbraucht
            matched_qty = remaining_qty
            oldest_lot.quantity -= matched_qty
        
        # Berechnung (alles in EUR, pro matched_qty):
        cost_basis = matched_qty * oldest_lot.cost_per_unit_eur
        buy_commission = matched_qty * oldest_lot.commission_per_unit_eur
        proceeds = matched_qty * sell_price_per_unit_eur
        sell_commission = matched_qty * sell_commission_per_unit_eur
        
        gain_loss = proceeds - cost_basis - buy_commission - sell_commission
        
        # Nur erfassen wenn Verkauf im relevanten Steuerjahr
        sell_year = trade.settle_date.year if trade.settle_date else trade.trade_date.date().year
        
        record = RealizedGainRecord(
            symbol=trade.symbol,
            asset_category=trade.asset_category,
            buy_date=oldest_lot.buy_date,
            sell_date=trade.trade_date.date(),
            settle_date=trade.settle_date,
            quantity=matched_qty,
            cost_basis_eur=cost_basis,
            buy_commission_eur=buy_commission,
            proceeds_eur=proceeds,
            sell_commission_eur=sell_commission,
            gain_loss_eur=gain_loss,
            holding_period_days=(trade.trade_date.date() - oldest_lot.buy_date).days,
            tax_year=sell_year
        )
        results.append(record)
        remaining_qty -= matched_qty
    
    return results
@dataclass
class FifoLotRecord:
trade_id: int
symbol: str
buy_date: date
quantity: Decimal
cost_per_unit_eur: Decimal
commission_per_unit_eur: Decimal
asset_category: str

@dataclass
class RealizedGainRecord:
symbol: str
asset_category: str
buy_date: date
sell_date: date
settle_date: date
quantity: Decimal
cost_basis_eur: Decimal
buy_commission_eur: Decimal
proceeds_eur: Decimal
sell_commission_eur: Decimal
gain_loss_eur: Decimal
holding_period_days: int
tax_year: int

@dataclass
class FifoResult:
realized_gains: list[RealizedGainRecord] # Nur für das Steuerjahr
open_positions: dict[str, list[FifoLotRecord]] # Verbleibende Lots
errors: list[str]


@property
def gains_for_tax_year(self) -> list[RealizedGainRecord]:
    """Nur Gains im gewählten Steuerjahr"""
    return [g for g in self.realized_gains if g.tax_year == self.tax_year]
TESTS (tests/test_engine/test_fifo.py) - SEHR WICHTIG, viele Szenarien:

Test 1 - Einfacher Kauf und Verkauf:
Kauf: 100 AAPL @ $150, Kommission $1, am 2024-01-15, Kurs 1 EUR = 1.10 USD
-> cost_per_unit_eur = (150/1.10) = 136.36 EUR
Verkauf: 100 AAPL @ $200, Kommission $1, am 2024-06-15, Kurs 1 EUR = 1.08 USD
-> proceeds_per_unit_eur = (200/1.08) = 185.19 EUR
-> Gewinn = 100 * (185.19 - 136.36) - Kommissionen = ca. 4883 EUR - Kommissionen
Prüfe: gain_loss_eur ist korrekt berechnet

Test 2 - FIFO-Reihenfolge:
Kauf 1: 50 AAPL @ $100 am 2023-01-01 (Lot 1)
Kauf 2: 50 AAPL @ $200 am 2023-06-01 (Lot 2)
Verkauf: 75 AAPL @ $150 am 2024-03-01
-> FIFO: 50 aus Lot 1 (Kauf @ $100) + 25 aus Lot 2 (Kauf @ $200)
-> Lot 2 hat danach noch 25 Stück übrig
Prüfe: 2 RealizedGainRecords, mit korrekten Mengen und Kaufpreisen

Test 3 - Jahresübergreifend:
Kauf: 100 MSFT @ $300 am 2022-05-01
Verkauf: 100 MSFT @ $400 am 2024-08-01
Steuerjahr = 2024
Prüfe: Der Gewinn wird dem Steuerjahr 2024 zugeordnet
Prüfe: Die Anschaffungskosten stammen aus 2022

Test 4 - Teilverkauf:
Kauf: 100 AAPL @ $100
Verkauf 1: 30 AAPL @ $120
Verkauf 2: 70 AAPL @ $130
Prüfe: Nach Verkauf 1 sind 70 Stück im Stack
Prüfe: Nach Verkauf 2 ist der Stack leer

Test 5 - Mehrere Symbole gleichzeitig:
Kauf: 100 AAPL @ $100 und 200 MSFT @ $50
Verkauf: 100 AAPL @ $120
Prüfe: MSFT-Stack ist unverändert (200 Stück)

Test 6 - Verkauf ohne vorherigen Kauf (Short Sell):
Verkauf: 100 XYZ @ $50 (kein Kauf vorher)
Prüfe: Error wird geloggt, kein Crash

Test 7 - Exakte Dezimalrechnung:
Kauf: 3 Stück @ 10.00 EUR, Kommission 1.50 EUR
-> cost_per_unit = 10.00, commission_per_unit = 0.50
Verkauf: 2 Stück @ 15.00 EUR, Kommission 1.00 EUR
-> Gewinn = 2 * 15.00 - 2 * 10.00 - 2 * 0.50 - 1.00 = 30 - 20 - 1 - 1 = 8.00 EUR
Prüfe: gain_loss_eur == Decimal("8.00") (exakt, kein Float-Fehler!)



**Validierung**: `pytest tests/test_engine/test_fifo.py -v` → 7+ Tests grün

---

### Phase 8: Steuerliche Kategorisierung

**Ziel**: Zuordnung der realisierten Gewinne zu den richtigen Verlustverrechnungstöpfen.
PROMPT FÜR AI-AGENT:

Erstelle src/ibkr_tax/engine/tax_categorizer.py.

Dieses Modul ordnet die realisierten Gewinne den korrekten steuerlichen Kategorien zu.

DEUTSCHES STEUERRECHT (Stand 2025):

AKTIEN-VERRECHNUNGSTOPF (§20 Abs. 6 Satz 4 EStG):

Verluste aus der Veräußerung von AKTIEN können NUR mit Gewinnen
aus der Veräußerung von AKTIEN verrechnet werden
asset_category == "STK" UND es ist ein VERKAUF (nicht Dividende!)
Verluste: tax_category = "aktien_verlust"
Gewinne: tax_category = "aktien_gewinn"
TERMINGESCHÄFTE (§20 Abs. 6 Satz 5 EStG - AUFGEHOBEN durch JStG 2024):

Optionen ("OPT"), Futures ("FUT")
KEINE separate Verlustbeschränkung mehr seit JStG 2024!
Gewinne UND Verluste: tax_category = "termingeschaeft"
Diese werden im allgemeinen Topf mit Dividenden, Zinsen etc. verrechnet
ALLGEMEINER TOPF:

Dividenden: tax_category = "dividende"
Zinsen: tax_category = "zinsen"
Sonstige: tax_category = "sonstige"
Quellensteuer: tax_category = "quellensteuer"
class TaxCategorizer:


def categorize_gains(self, gains: list[RealizedGainRecord]) -> CategorizedResult:
    """Ordnet jeden Gain einer steuerlichen Kategorie zu"""
    
    for gain in gains:
        if gain.asset_category == "STK":
            if gain.gain_loss_eur >= 0:
                gain.tax_category = "aktien_gewinn"
            else:
                gain.tax_category = "aktien_verlust"
        elif gain.asset_category in ("OPT", "FUT"):
            gain.tax_category = "termingeschaeft"
        else:
            gain.tax_category = "sonstige"

def calculate_summary(self, gains: list[RealizedGainRecord], 
                      dividends: list[Dividend],
                      withholding_taxes: list[WithholdingTax],
                      interest: list[Interest]) -> TaxSummary:
    """Berechnet die Zusammenfassung für die Anlage KAP"""
    
@dataclass
class TaxSummary:
# Aktien-Topf
aktien_gewinne: Decimal # Summe aller Aktiengewinne
aktien_verluste: Decimal # Summe aller Aktienverluste (negativ)
aktien_netto: Decimal # Verrechnung innerhalb des Topfes
aktien_verlustvortrag: Decimal # Überschießende Verluste -> Vortrag


# Allgemeiner Topf
termingeschaefte_netto: Decimal  # Saldo Optionen + Futures
dividenden_brutto: Decimal       # Brutto-Dividenden in EUR
zinsen: Decimal                  # Zinserträge in EUR
sonstige_ertraege: Decimal       

# Quellensteuer
quellensteuer_gesamt: Decimal    # Einbehaltene ausländische Quellensteuer
quellensteuer_anrechenbar: Decimal  # Maximal anrechenbar (DBA-Limits)

# Gesamtergebnis
allgemeiner_topf_netto: Decimal  # Termingeschäfte + Dividenden + Zinsen + Sonstige

# Für Anlage KAP
zeile_7: Decimal = Decimal("0")  # Dem inl. Steuerabzug unterlegen (bei IBKR: 0!)
zeile_8: Decimal = Decimal("0")  # NICHT dem inl. Steuerabzug unterlegen (ALLES hier!)
zeile_9: Decimal = Decimal("0")  # Gewinn aus Aktienveräußerungen
zeile_10: Decimal = Decimal("0") # Verlust aus Aktienveräußerungen
zeile_15: Decimal = Decimal("0") # Anrechenbare ausländische Quellensteuer

def calculate_kap_lines(self):
    """Berechnet die Zeilen für die Anlage KAP"""
    self.zeile_8 = self.dividenden_brutto + self.zinsen + self.termingeschaefte_netto + self.sonstige_ertraege
    self.zeile_9 = max(self.aktien_netto, Decimal("0"))
    self.zeile_10 = min(self.aktien_netto, Decimal("0"))
    self.zeile_15 = self.quellensteuer_anrechenbar
Tests in tests/test_engine/test_tax_categorizer.py:

Test 1 - Aktiengewinn wird korrekt kategorisiert:
STK, gain_loss = +500 EUR -> tax_category = "aktien_gewinn"

Test 2 - Aktienverlust wird korrekt kategorisiert:
STK, gain_loss = -300 EUR -> tax_category = "aktien_verlust"

Test 3 - Optionsgewinn wird als Termingeschäft kategorisiert:
OPT, gain_loss = +1000 EUR -> tax_category = "termingeschaeft"

Test 4 - Optionsverlust wird als Termingeschäft kategorisiert (KEIN separater Topf!):
OPT, gain_loss = -42000 EUR -> tax_category = "termingeschaeft"
Prüfe: KEINE Begrenzung auf 20.000 EUR!

Test 5 - Verlustverrechnungstöpfe:
Aktiengewinne: +2000, Aktienverluste: -3000
-> aktien_netto = -1000 (Verlustvortrag!)
-> Aktienverluste werden NICHT mit Optionsgewinnen verrechnet

Test 6 - Allgemeiner Topf:
Optionsgewinne: +5000, Optionsverluste: -42000
Dividenden: +3000, Zinsen: +500
-> termingeschaefte_netto = -37000
-> allgemeiner_topf_netto = -37000 + 3000 + 500 = -33500

Test 7 - Quellensteuer:
US-Dividende: +1000 EUR, US-Quellensteuer: -150 EUR (15%)
-> quellensteuer_anrechenbar = 150 EUR (USA: 15% via DBA anrechenbar)

Test 8 - Anlage KAP Zeilen:
Prüfe, dass zeile_8, zeile_9, zeile_10, zeile_15 korrekt berechnet werden



**Validierung**: `pytest tests/test_engine/test_tax_categorizer.py -v`

---

### Phase 9: Options-Sonderfälle

**Ziel**: Korrekte Behandlung von Options-Verfall, Ausübung und Assignment.
PROMPT FÜR AI-AGENT:

Erstelle src/ibkr_tax/engine/options_handler.py.

Optionen haben steuerliche Sonderfälle, die korrekt behandelt werden müssen:

OPTION GESCHLOSSEN (Closing Trade):

Normaler Kauf/Verkauf, wird wie ein regulärer Trade via FIFO abgerechnet
Keine Besonderheit
OPTION VERFÄLLT WERTLOS (Expiration):

Käufer: Der gezahlte Prämienpreis ist ein realisierter VERLUST
Verkäufer (Writer): Die erhaltene Prämie ist ein realisierter GEWINN
In IBKR-Daten: Trade mit quantity und price=0, oder spezieller "Expiration"-Eintrag
Steuerlich: Seit BFH VIII R 3/21 ist der wertlose Verfall steuerlich anerkannt!
OPTION AUSGEÜBT (Exercise) / ZUGEWIESEN (Assignment):

Die Optionsprämie wird auf den Aktienpreis angerechnet:
Long Call ausgeübt: Anschaffungskosten der Aktie = Strike + gezahlte Prämie
Short Put zugewiesen: Anschaffungskosten der Aktie = Strike - erhaltene Prämie
Long Put ausgeübt: Veräußerungserlös = Strike - gezahlte Prämie
Short Call zugewiesen: Veräußerungserlös = Strike + erhaltene Prämie
Die Option selbst wird NICHT als separater Gewinn/Verlust erfasst!
In IBKR-Daten: Erkennbar am Code "A" (Assignment) oder "Ex" (Exercise)
class OptionsHandler:


def identify_expirations(self, trades: list[Trade]) -> list[Trade]:
    """Identifiziert verfallene Optionen in den Trade-Daten
    IBKR markiert diese typischerweise mit:
    - quantity != 0 aber price = 0
    - Oder einem speziellen Code/Notes-Feld
    - Oder in Corporate Actions als "Expiration"
    """

def identify_exercises_assignments(self, trades: list[Trade]) -> list[ExerciseEvent]:
    """Identifiziert Ausübungen/Zuweisungen
    Sucht nach Trades mit Code 'A' (Assignment) oder 'Ex' (Exercise)
    Verknüpft die Option mit dem resultierenden Aktien-Trade
    """

def adjust_stock_cost_for_exercise(self, stock_trade: Trade, 
                                    option_trade: Trade) -> Trade:
    """Passt die Anschaffungskosten/Erlöse des Aktien-Trades an
    
    Wenn Long Call ausgeübt:
    - stock_trade.cost_basis += option_premium_paid
    
    Wenn Short Put zugewiesen:
    - stock_trade.cost_basis -= option_premium_received
    """
@dataclass
class ExerciseEvent:
option_trade: Trade
stock_trade: Trade
exercise_type: Literal["EXERCISE", "ASSIGNMENT"]

Tests in tests/test_engine/test_options.py:

Test 1 - Option geschlossen (Closing Trade):
Verkauf (Open): 5 SPY Put @ $3.50, Prämie erhalten: $1750
Kauf (Close): 5 SPY Put @ $2.00, Prämie bezahlt: $1000
-> Gewinn: $750 (in EUR umgerechnet)
-> Kategorie: termingeschaeft

Test 2 - Long Call verfällt wertlos:
Kauf: 1 AAPL Call @ $5.00 (500 EUR gezahlt)
Option verfällt (expiry)
-> Verlust: -500 EUR
-> Kategorie: termingeschaeft

Test 3 - Short Put verfällt wertlos:
Verkauf: 1 AAPL Put @ $3.00 (300 EUR erhalten)
Option verfällt (expiry)
-> Gewinn: +300 EUR
-> Kategorie: termingeschaeft

Test 4 - Long Call ausgeübt (Exercise):
Kauf: 1 AAPL Call Strike $150 @ $10 (Prämie: $1000)
Ausübung: Kauf 100 AAPL @ $150 (eigentlich @ $160 effektiv)
-> Aktien-Anschaffungskosten: (150 + 10) * 100 = $16000
-> KEIN separater Optionsgewinn/-verlust!

Test 5 - Short Put zugewiesen (Assignment):
Verkauf: 1 AAPL Put Strike $200 @ $15 (Prämie erhalten: $1500)
Zuweisung: Kauf 100 AAPL @ $200 (effektiv @ $185)
-> Aktien-Anschaffungskosten: (200 - 15) * 100 = $18500
-> KEIN separater Optionsgewinn/-verlust!



**Validierung**: `pytest tests/test_engine/test_options.py -v`

---

### Phase 10: Corporate Actions (Stock Splits)
PROMPT FÜR AI-AGENT:

Erstelle src/ibkr_tax/engine/corporate_actions.py.

Corporate Actions wie Aktiensplits verändern die FIFO-Stacks:

STOCK SPLIT (z.B. 4:1):

Die Anzahl der Aktien vervierfacht sich
Der Preis pro Aktie wird geviertelt
Die GESAMTEN Anschaffungskosten bleiben GLEICH!
Beispiel: 100 Aktien @ 400 EUR -> 400 Aktien @ 100 EUR (Gesamtwert unverändert)
REVERSE SPLIT (z.B. 1:10):

Umgekehrt: Weniger Aktien, höherer Preis
Gesamtkosten bleiben gleich
MERGER/SPINOFF (Phase 2, erstmal nicht implementieren):

Sehr komplex, erfordert manuelle Eingabe der Aufteilungsverhältnisse
class CorporateActionsHandler:


def process_split(self, fifo_engine: FifoEngine, symbol: str, ratio: str):
    """
    Verarbeitet einen Aktiensplit.
    ratio: z.B. "4:1" (4 neue Aktien für 1 alte)
    
    Für jedes Lot im FIFO-Stack des Symbols:
    - lot.quantity *= split_factor (z.B. * 4)
    - lot.cost_per_unit_eur /= split_factor (z.B. / 4)
    - lot.commission_per_unit_eur /= split_factor
    
    Die Gesamtkosten pro Lot bleiben exakt gleich!
    """

def parse_split_ratio(self, ratio: str) -> Decimal:
    """Parst '4:1' zu Decimal('4'), '1:10' zu Decimal('0.1')"""
Tests in tests/test_engine/test_corporate_actions.py:

Test 1 - Forward Split 4:1:
Kauf: 100 AAPL @ 400 EUR (Gesamtkosten: 40000 EUR)
Split 4:1
-> Stack: 400 AAPL @ 100 EUR (Gesamtkosten: 40000 EUR, unverändert!)
Verkauf: 400 AAPL @ 120 EUR
-> Gewinn: 400 * (120 - 100) = 8000 EUR

Test 2 - Reverse Split 1:10:
Kauf: 1000 XYZ @ 1 EUR (Gesamtkosten: 1000 EUR)
Reverse Split 1:10
-> Stack: 100 XYZ @ 10 EUR (Gesamtkosten: 1000 EUR, unverändert!)

Test 3 - Split mit mehreren FIFO-Lots:
Kauf 1: 50 AAPL @ 100 EUR
Kauf 2: 50 AAPL @ 200 EUR
Split 2:1
-> Lot 1: 100 AAPL @ 50 EUR
-> Lot 2: 100 AAPL @ 100 EUR



**Validierung**: `pytest tests/test_engine/test_corporate_actions.py -v`

---

### Phase 11: Excel-Export für Steuerberater
PROMPT FÜR AI-AGENT:

Erstelle src/ibkr_tax/reports/excel_export.py.

Der Excel-Export muss so formatiert sein, dass ein Steuerberater
sofort damit arbeiten kann. Nutze openpyxl für formatierte Ausgabe.

class TaxReportExporter:

text

def generate_report(self, summary: TaxSummary, 
                    gains: list[RealizedGainRecord],
                    dividends: list[Dividend],
                    withholding_taxes: list[WithholdingTax],
                    interest: list[Interest],
                    tax_year: int) -> bytes:
    """Generiert eine Excel-Datei im Speicher und gibt sie als bytes zurück"""
    
    wb = Workbook()
    
    # Sheet 1: Übersicht / Zusammenfassung
    self._create_summary_sheet(wb, summary, tax_year)
    
    # Sheet 2: Anlage KAP Zuordnung
    self._create_kap_sheet(wb, summary)
    
    # Sheet 3: Einzelnachweis Aktien
    self._create_stock_gains_sheet(wb, stock_gains)
    
    # Sheet 4: Einzelnachweis Termingeschäfte (Optionen)
    self._create_options_gains_sheet(wb, option_gains)
    
    # Sheet 5: Dividenden
    self._create_dividends_sheet(wb, dividends)
    
    # Sheet 6: Quellensteuer
    self._create_withholding_tax_sheet(wb, withholding_taxes)
    
    # Sheet 7: Zinsen
    self._create_interest_sheet(wb, interest)
    
    return save_virtual_workbook(wb)
Formatierung:

Datumsformat: DD.MM.YYYY (deutsches Format!)
Zahlenformat: #.##0,00 € (deutsches Zahlenformat mit Komma als Dezimaltrenner)
Header fett, grauer Hintergrund
Negative Beträge in Rot
Summenzeile am Ende jedes Sheets
Spaltenbreiten automatisch anpassen
Sheet "Übersicht" soll enthalten:

Kategorie	Betrag (EUR)
Aktiengewinne	5.230,15
Aktienverluste	-1.200,00
Aktien Netto	4.030,15
Optionsgewinne	12.500,00
Optionsverluste	-42.300,00
Termingeschäfte Netto	-29.800,00
Dividenden (brutto)	3.450,00
Zinsen	520,00
Anrechenbare Quellensteuer	-517,50
ALLGEMEINER TOPF NETTO	-25.830,00
Sheet "Einzelnachweis_Aktien" Spalten:
Symbol | ISIN | Kaufdatum | Verkaufsdatum | Menge | Anschaffungskosten (EUR) | Veräußerungserlös (EUR) | Kaufgebühren (EUR) | Verkaufsgebühren (EUR) | Gewinn/Verlust (EUR) | Haltedauer (Tage)

Tests in tests/test_reports/test_excel_export.py:

Test: Excel-Datei wird erzeugt (bytes sind nicht leer)
Test: Alle 7 Sheets sind vorhanden
Test: Übersicht-Sheet enthält korrekte Summen
Test: Datumsformat ist DD.MM.YYYY
Test: Negative Beträge sind formatiert
text


**Validierung**: `pytest tests/test_reports/ -v`

---

### Phase 12: Streamlit UI
PROMPT FÜR AI-AGENT:

Erstelle die Streamlit-App in src/ibkr_tax/ui/app.py.

Die App soll folgende Seiten haben (Multi-Page Streamlit App):

Seite 1 - Import:

File-Uploader für Flex Query XML oder Activity Statement CSV
"Datei analysieren" Button
Zeigt an: Anzahl gefundene Trades, Dividenden, etc.
"In Datenbank importieren" Button
Fortschrittsbalken während des Imports
Zusammenfassung nach Import (ImportResult)
Seite 2 - Übersicht:

Dropdown: Steuerjahr auswählen (basierend auf vorhandenen Daten)
"FIFO berechnen" Button
Zeigt TaxSummary als Tabelle
Zeigt Anlage KAP Zeilen
Seite 3 - Einzelnachweise:

Tabs: Aktien | Optionen | Dividenden | Zinsen
Jeder Tab zeigt eine Datatable mit den Einzelposten
Sortier- und Filtermöglichkeiten
Suchfeld für Symbole
Seite 4 - Export:

"Excel-Report generieren" Button
st.download_button für den Download
Vorschau der Zusammenfassung
Sidebar:

Steuerjahr-Auswahl (beeinflusst alle Seiten)
DB-Status (Anzahl importierter Trades, etc.)
"Datenbank zurücksetzen" Button (mit Bestätigung!)
Erstelle zunächst nur Seite 1 (Import) vollständig funktional.
Die anderen Seiten können als Platzhalter angelegt werden.

Achte auf:

st.session_state für die Persistenz zwischen Seiten
Error-Handling mit st.error() und st.warning()
st.spinner() für lange Operationen
st.cache_resource für DB-Connection
text


**Validierung**: `streamlit run src/ibkr_tax/ui/app.py` → App startet, Upload funktioniert

---

### Phase 13: Integration Test (End-to-End)
PROMPT FÜR AI-AGENT:

Erstelle einen vollständigen End-to-End-Test in tests/test_integration/test_full_pipeline.py.

Dieser Test simuliert den kompletten Workflow:

Erstelle eine realistische Test-XML-Datei (Flex Query) mit:

Account: U9999999
Zeitraum: 2022-01-01 bis 2024-12-31 (3 Jahre!)
Trades:
a) 2022-03-15: BUY 100 AAPL @ $150.00, Comm: -$1.00 (USD)
b) 2022-06-01: BUY 200 MSFT @ $280.00, Comm: -$1.00 (USD)
c) 2023-01-10: BUY 50 AAPL @ $130.00, Comm: -$1.00 (USD)
d) 2023-09-01: SELL (Open) 5 SPY Put 2024-03-15 Strike $450 @ $12.00, Comm: -$5.25 (USD)
e) 2024-02-01: BUY (Close) 5 SPY Put 2024-03-15 Strike $450 @ $5.00, Comm: -$5.25 (USD)
f) 2024-04-15: SELL 120 AAPL @ $185.00, Comm: -$1.00 (USD)
-> FIFO: 100 aus Kauf a) + 20 aus Kauf c)
g) 2024-08-01: SELL 100 MSFT @ $420.00, Comm: -$1.00 (USD)
-> FIFO: 100 aus Kauf b)

Dividenden (2024):
h) 2024-03-15: AAPL Dividend $0.25/share, 150 shares = $37.50
i) 2024-06-15: MSFT Dividend $0.75/share, 100 shares = $75.00

Quellensteuer (2024):
j) 2024-03-15: AAPL -$5.63 (15% US)
k) 2024-06-15: MSFT -$11.25 (15% US)

Führe den kompletten Pipeline durch:

Parse XML
Import in DB (mit EUR-Umrechnung)
FIFO-Berechnung für Steuerjahr 2024
Steuerliche Kategorisierung
Excel-Export
Prüfungen:

Trade f) nutzt FIFO korrekt: 100 Stück aus 2022 + 20 Stück aus 2023
Option e)-d) ergibt Gewinn: (12-5) * 5 * 100 = $3500 in EUR
Aktiengewinne und Optionsgewinne sind in separaten Kategorien
Quellensteuer wird korrekt zugeordnet
Excel hat alle Sheets
Übersicht-Summen stimmen
Nach dem FIFO bleiben 30 AAPL (aus Kauf c) und 100 MSFT (aus Kauf b) als offene Positionen
Prüfe auch den Sonderfall:

Wenn wir Steuerjahr 2023 auswählen, darf NUR der Options-Trade d)-e) NICHT erscheinen
Die Verkäufe f) und g) erscheinen nur im Steuerjahr 2024
text


**Validierung**: `pytest tests/test_integration/ -v --tb=long`

---

### Phase 14: Währungsgewinne (§23 EStG) – Optional, hohe Komplexität
PROMPT FÜR AI-AGENT:

HINWEIS: Dies ist ein optionales Feature mit sehr hoher Komplexität.
Nur implementieren wenn die Grundfunktionen stabil laufen!

Wenn ein Steuerpflichtiger bei IBKR Fremdwährungsguthaben hält (z.B. USD auf dem Multi-Currency-Account),
kann der Verkauf dieser Währung ein privates Veräußerungsgeschäft nach §23 Abs. 1 Nr. 2 EStG sein,
wenn die Währung weniger als 1 Jahr gehalten wurde.

Beispiel:

01.03.2024: Verkauf von 100 AAPL für $20.000 -> USD landen auf dem Konto
15.08.2024: Kauf von MSFT für $10.000 -> USD werden "verbraucht"
-> Die $10.000 wurden < 1 Jahr gehalten
-> Wenn der EUR/USD-Kurs sich zwischenzeitlich geändert hat: Währungsgewinn/-verlust!
Für die Implementierung:

Führe ein separates FIFO für jede Fremdwährung (USD-Stack, GBP-Stack, etc.)
Jeder Zugang von Fremdwährung (Verkaufserlöse, Dividenden in USD) ist ein "Kauf" von USD
Jeder Abgang von Fremdwährung (Kaufpreis, Gebühren in USD) ist ein "Verkauf" von USD
Wenn zwischen Zugang und Abgang < 365 Tage: steuerpflichtiger Währungsgewinn
Freigrenze beachten: §23 Abs. 3 Satz 5 EStG: 1.000 EUR (seit 2024)
ACHTUNG: Dies ist extrem komplex und fehleranfällig.
Viele Steuerberater ignorieren Währungsgewinne bei Brokern oder behandeln sie vereinfacht.
Implementiere dies nur als optionales Feature mit klarem Warnhinweis!

text


---

## 7. Zusammenfassung: Build-Reihenfolge
Phase 0: Projekt-Setup → pytest ✓
Phase 1: DB-Models → pytest ✓
Phase 2: Pydantic-Schemas → pytest ✓
Phase 3: EZB-Wechselkurse → pytest ✓
Phase 4: Flex Query XML Parser → pytest ✓
Phase 5: CSV Activity Statement Parser → pytest ✓
Phase 6: Import-Pipeline (Parser → DB) → pytest ✓
Phase 7: FIFO-Engine ⭐ → pytest ✓ (Kernstück!)
Phase 8: Steuerliche Kategorisierung → pytest ✓
Phase 9: Options-Sonderfälle → pytest ✓
Phase 10: Corporate Actions → pytest ✓
Phase 11: Excel-Export → pytest ✓
Phase 12: Streamlit UI → manueller Test
Phase 13: Integration-Test E2E → pytest ✓
Phase 14: Währungsgewinne (optional) → pytest ✓

text


### Kritischer Pfad (Minimum Viable Product):

**Phasen 0 → 1 → 2 → 3 → 4 → 6 → 7 → 8 → 11 → 12**

Das ergibt ein funktionierendes Tool, das:
- Flex Query XML einliest ✓
- In eine DB schreibt ✓
- FIFO berechnet ✓
- Steuerlich kategorisiert ✓
- Excel für den Steuerberater exportiert ✓
- Ein UI zum Bedienen hat ✓

Die restlichen Phasen (CSV-Parser, Optionen, Corporate Actions, Währungsgewinne) sind Erweiterungen.

---

## 8. Wichtige Hinweise für die AI-Agenten

### Do's:
- **IMMER `decimal.Decimal`** für Geldbeträge, NIEMALS `float`
- **IMMER Tests zuerst** schreiben (oder zumindest parallel)
- **IMMER Settle-Date** für die Steuerjahr-Zuordnung verwenden (nicht Trade-Date!)
- **IMMER alle Vorjahre** für FIFO einlesen, auch wenn nur ein Jahr ausgewertet wird
- **IMMER EZB-Kurse** verwenden, keine Drittanbieter-Wechselkurse

### Don'ts:
- **KEIN `float`** für Geldbeträge (Rundungsfehler!)
- **KEINE Durchschnittskosten** – deutsches Recht verlangt FIFO
- **KEINE 20.000€-Grenze** für Termingeschäfte (seit JStG 2024 aufgehoben!)
- **KEINE Verrechnung** von Aktienverlusten mit Dividenden/Optionsgewinnen
- **KEIN Hardcoding** von Wechselkursen – immer EZB-Tageskurs