import streamlit as st
import tempfile
import os
from ibkr_tax.db.engine import get_engine, get_session, migrate_schema
from ibkr_tax.services.pipeline import run_import
from ibkr_tax.services.fifo_runner import FIFORunner
from ibkr_tax.services.tax_aggregator import TaxAggregatorService
from ibkr_tax.services.maintenance import MaintenanceService
from ibkr_tax.services.excel_export import ExcelExportService
from ibkr_tax.db.repository import get_distinct_account_ids, get_tax_years_for_account, get_manual_positions, add_manual_position, delete_manual_position
from ibkr_tax.services.tax_tooltips import KAP_TOOLTIPS, TAX_POOL_EXPLANATIONS
from ibkr_tax.models.database import Base, Account
from decimal import Decimal
import pandas as pd
from datetime import date
from sqlalchemy import select

# --- Translations ---
UI_STRINGS = {
    "en": {
        "sidebar_title": "IBKR2KAP",
        "sidebar_info": "Local-first tax assistant for German IBKR users.",
        "lang_label": "Global Language / Sprache",
        "title": "🛡️ IBKR2KAP — Tax Reporting",
        "import_header": "Import IBKR Data",
        "import_desc": "Upload your **Flex Query XML** or **Activity Statement CSV** files here. Data is stored locally.",
        "btn_process_xml": "Process XML",
        "btn_process_csv": "Process CSV",
        "fifo_header": "FIFO Matching & Tax Allocation",
        "btn_run_fifo": "🚀 Run FIFO Engine (All Accounts)",
        "manual_header": "📝 Manual Cost-Basis Entry",
        "report_header": "Anlage KAP Generation",
        "btn_gen_report": "📊 Generate Tax Report",
        "status_parsing": "Parsing {}...",
        "status_success": "Successfully processed {}",
        "status_db_reset": "Database has been reset.",
        "missing_cost_warning": "⚠️ **Missing Cost Basis Detected**",
        "save_btn": "💾 Save Anlage KAP Excel Report",
        "status_header": "📢 Status",
        "status_ready": "Ready.",
        "upload_xml": "Upload Flex XML",
        "upload_csv": "Upload Activity CSV (Fallback)",
        "success_processed": "Successfully processed {}",
        "warning_unsupported": "⚠️ **Unsupported Data Entities Found in {}**",
        "danger_zone": "🚨 Dangerous Zone",
        "reset_header": "Reset All Data",
        "reset_warning": "This will permanently delete all trades, cash transactions, and processed results. Only account IDs will be preserved.",
        "reset_confirm": "I understand that this action is irreversible",
        "reset_btn": "🚨 Reset Database",
        "reset_success": "Database has been reset. All transaction tables are now empty.",
        "fifo_desc": "Run the FIFO matching engine to calculate realized gains and losses across all accounts.",
        "fifo_running": "Running FIFO Engine...",
        "fifo_complete": "FIFO Engine Complete",
        "manual_desc": """If you sold positions that were **acquired before your XML data range**, they will appear as
"Missing Cost Basis" warnings in the Anlage KAP report.

Use this form to provide the **acquisition date** and **cost basis** for those positions.
After adding entries, **re-run the FIFO Engine** in the Tax Processing tab.""",
        "no_accounts": "No accounts found. Import IBKR data first.",
        "account_label": "Account",
        "account_not_found": "Account not found in database.",
        "existing_manual": "Existing Manual Positions ({})",
        "delete_manual_expander": "🗑️ Delete a Manual Position",
        "delete_select_label": "Select position to delete",
        "delete_btn": "🗑️ Delete Selected Position",
        "delete_success": "Position deleted. Re-run the FIFO Engine to update results.",
        "delete_error": "Could not find position to delete.",
        "no_manual": "No manual positions for this account yet.",
        "add_manual_header": "Add New Manual Position",
        "symbol_label": "Symbol (e.g. AAPL)",
        "asset_cat_label": "Asset Category",
        "buy_sell_label": "Buy/Sell",
        "open_close_label": "Open/Close",
        "qty_label": "Quantity",
        "price_label": "Trade Price",
        "currency_label": "Currency",
        "fx_label": "FX Rate to EUR",
        "trade_date_label": "Trade Date",
        "settle_date_label": "Settlement Date",
        "proceeds_label": "Proceeds",
        "comm_label": "IB Commission (Trade)",
        "desc_label": "Description (optional)",
        "add_btn": "➕ Add Manual Position",
        "err_sym_req": "Symbol is required.",
        "report_desc": "Generate the final tax report figures for a specific account and year.",
        "err_no_acc_db": "No accounts found in the database. Please import some IBKR data first.",
        "acc_multi_label": "IBKR Account ID(s)",
        "select_at_least_one": "Select at least one account.",
        "no_common_years": "No common tax years found for these accounts.",
        "tax_year_label": "Tax Year",
        "generating_report": "Generating report for {}...",
        "missing_cost_msg": "The following sell trades do not have corresponding buy trades. This will lead to an incorrect taxable gain/loss calculation (treated as 100% gain if not resolved).",
        "prefill_btn": "📝 Prefill Manual",
        "prefill_success": "Prefilled {}! Go to **📝 Manual Positions** tab.",
        "prefill_info": "💡 You can provide cost basis for these positions in the **📝 Manual Positions** tab, then re-run the FIFO Engine.",
        "gen_anyway": "Generate report anyway despite missing data",
        "report_summary_comb": "Combined Report Summary ({})",
        "report_summary_single": "Report Summary for {} ({})",
        "accounts_included": "📊 **Accounts Included**: {}",
        "kap7_label": "KAP Line 7 (Dividends / Interest / Payments / Other)",
        "kap8_label": "KAP Line 8 (Stock Realized Gains)",
        "kap9_label": "KAP Line 9 (Stock Realized Losses)",
        "kap10_label": "KAP Line 10 (Derivatives Net)",
        "kap10_gains": "  - thereof Gains",
        "kap10_losses": "  - thereof Losses",
        "kap15_label": "KAP Line 15 (Withholding Tax)",
        "pool_summary_header": "Summary by Tax Pools",
        "aktien_pool_label": "Stock Pool (Net)",
        "allg_pool_label": "General Pool Result",
        "so_fx_total_label": "Anlage SO (FX Total)",
        "so_header": "Anlage SO (§ 23 EStG Foreign Currency Transactions)",
        "so_fx_gains_label": "SO FX Total Gain",
        "so_fx_taxable_label": "SO FX Taxable (< 1 y.)",
        "so_fx_taxfree_label": "SO FX Tax-Free (> 1 y.)",
        "freigrenze_applied": "ℹ️ **Exemption Limit Applied**: Since private disposal gains (§ 23) are below €1,000, they remain tax-free.",
        "freigrenze_exceeded": "⚠️ **Exemption Limit Exceeded**: Gains of €1,000 or more are fully taxable.",
        "margin_header": "💰 Margin Costs (Info)",
        "margin_label": "Margin Interest (Broker Interest Paid)",
        "margin_warning": """⚠️ **Not Deductible**: Margin interest (Broker Interest Paid) represents 
income-related expenses that, according to § 20 Abs. 9 EStG, may not be 
deducted from capital income. This amount is purely informative and does 
**not** flow into the Anlage KAP calculation. Details in the Excel export 
on the **Margin Costs (Info)** sheet.""",
        "individual_breakdowns": "Individual Account Breakdowns",
        "details_for": "📊 Details for {}",
        "what_do_lines_mean": "ℹ️ What do these lines mean?",
        "table_header_line": "Line",
        "table_header_name": "Name",
        "table_header_desc": "Explanation",
        "line_7_name": "Capital Gains",
        "line_7_desc": "Dividends, interest, compensation payments, and other gains (ETFs, bonds)",
        "line_8_name": "Stock Gains",
        "line_8_desc": "Only positive gains from individual stock sales",
        "line_9_name": "Stock Losses",
        "line_9_desc": "Absolute value of stock losses — only offsettable against stock gains",
        "line_10_name": "Derivatives",
        "line_10_desc": "Net result from options and futures",
        "line_15_name": "Withholding Tax",
        "line_15_desc": "Creditable foreign taxes (e.g. US withholding tax)",
        "guide_footer": "> 📖 Detailed explanations can be found in the **\"Tax Guide\"** tab and in `docs/GERMAN_TAX_THEORY.md`.",
        "export_header": "📥 Export to Excel",
        "save_dialog_title": "Save Anlage KAP Report",
        "export_success": "Report saved successfully to `{}`!",
        "export_info": "You can now open the file in Excel.",
        "export_cancelled": "Save was cancelled.",
        "db_browser_header": "🗄️ Database Browser",
        "db_browser_desc": "Inspect raw data directly from the SQLite database.",
        "db_no_tables": "No tables found in the database.",
        "db_select_table": "Select Table to Inspect",
        "db_showing_data": "Showing data for **{}** ({} rows)",
        "guide_header": "📖 German Tax Guide for IBKR Users",
        "guide_desc": "This guide explains how IBKR2KAP maps your trades to the lines of **Anlage KAP** and which tax rules are applied.",
        "guide_lines_header": "📋 Anlage KAP — Lines Overview",
        "guide_pools_header": "⚖️ Tax Pools",
        "guide_fifo_header": "🔢 FIFO Principle (First-In-First-Out)",
        "guide_fx_header": "💱 Currency Conversion (FX)",
        "guide_ca_header": "🏢 Corporate Actions",
        "guide_opt_header": "📊 Options (Derivatives)",
        "guide_disclaimer": "⚠️ **Disclaimer**: This information does not constitute tax advice. For individual tax questions, please contact a **tax advisor**. Legal status: 2024/2025 (JStG 2024).",
        "guide_full_ref": "📄 The full reference can be found in `docs/GERMAN_TAX_THEORY.md` in the project directory.",
        "aktien_pool_explanation_info": "Stock losses can **only** be offset against stock gains (§ 20 Abs. 6 Sent. 5 EStG). Unoffsetted losses are carried forward.",
    },
    "de": {
        "sidebar_title": "IBKR2KAP",
        "sidebar_info": "Lokaler Steuer-Assistent für deutsche IBKR-Nutzer.",
        "lang_label": "Sprache / Language",
        "title": "🛡️ IBKR2KAP — Steuerbericht",
        "import_header": "IBKR Daten importieren",
        "import_desc": "Laden Sie Ihre **Flex Query XML** oder **Activity Statement CSV** Dateien hier hoch. Die Daten werden lokal gespeichert.",
        "btn_process_xml": "XML verarbeiten",
        "btn_process_csv": "CSV verarbeiten",
        "fifo_header": "FIFO-Matching & Steuerzuordnung",
        "btn_run_fifo": "🚀 FIFO-Engine starten (Alle Konten)",
        "manual_header": "📝 Manuelle Anschaffungskosten",
        "report_header": "Anlage KAP Erstellung",
        "btn_gen_report": "📊 Steuerbericht erstellen",
        "status_parsing": "Verarbeite {}...",
        "status_success": "{} erfolgreich verarbeitet",
        "status_db_reset": "Datenbank wurde zurückgesetzt.",
        "missing_cost_warning": "⚠️ **Fehlende Anschaffungskosten erkannt**",
        "save_btn": "💾 Anlage KAP Excel-Bericht speichern",
        "status_header": "📢 Status",
        "status_ready": "Bereit.",
        "upload_xml": "Flex XML hochladen",
        "upload_csv": "Activity CSV hochladen (Fallback)",
        "success_processed": "{} erfolgreich verarbeitet",
        "warning_unsupported": "⚠️ **Nicht unterstützte Datentypen in {} gefunden**",
        "danger_zone": "🚨 Risikozone",
        "reset_header": "Alle Daten zurücksetzen",
        "reset_warning": "Dies wird permanent alle Trades, Transaktionen und berechneten Ergebnisse löschen. Nur Account-IDs bleiben erhalten.",
        "reset_confirm": "Ich verstehe, dass diese Aktion unwiderruflich ist",
        "reset_btn": "🚨 Datenbank zurücksetzen",
        "reset_success": "Datenbank wurde zurückgesetzt. Alle Tabellen sind nun leer.",
        "fifo_desc": "Starten Sie die FIFO-Matching-Engine, um realisierte Gewinne und Verluste über alle Konten hinweg zu berechnen.",
        "fifo_running": "FIFO-Engine läuft...",
        "fifo_complete": "FIFO-Engine abgeschlossen",
        "manual_desc": """Wenn Sie Positionen verkauft haben, die **vor Ihrem XML-Datenbereich erworben** wurden, erscheinen diese als
Warnung "Fehlende Anschaffungskosten" im Anlage KAP Bericht.

Nutzen Sie dieses Formular, um das **Anschaffungsdatum** und die **Anschaffungskosten** nachzureichen.
Klicken Sie danach erneut auf **FIFO-Engine starten** im Tab Steuer-Verarbeitung.""",
        "no_accounts": "Keine Konten gefunden. Bitte zuerst IBKR-Daten importieren.",
        "account_label": "Konto",
        "account_not_found": "Konto nicht in der Datenbank gefunden.",
        "existing_manual": "Vorhandene manuelle Positionen ({})",
        "delete_manual_expander": "🗑️ Manuelle Position löschen",
        "delete_select_label": "Position zum Löschen auswählen",
        "delete_btn": "🗑️ Ausgewählte Position löschen",
        "delete_success": "Position gelöscht. Starten Sie die FIFO-Engine neu, um die Ergebnisse zu aktualisieren.",
        "delete_error": "Position konnte nicht gefunden werden.",
        "no_manual": "Noch keine manuellen Positionen für dieses Konto.",
        "add_manual_header": "Neue manuelle Position hinzufügen",
        "symbol_label": "Symbol (z.B. AAPL)",
        "asset_cat_label": "Anlageklasse",
        "buy_sell_label": "Kauf/Verkauf",
        "open_close_label": "Open/Close",
        "qty_label": "Menge",
        "price_label": "Handelspreis",
        "currency_label": "Währung",
        "fx_label": "Wechselkurs zu EUR",
        "trade_date_label": "Handelsdatum",
        "settle_date_label": "Settlement-Datum",
        "proceeds_label": "Erlös (Proceeds)",
        "comm_label": "IB-Provision (Trade)",
        "desc_label": "Beschreibung (optional)",
        "add_btn": "➕ Manuelle Position hinzufügen",
        "err_sym_req": "Symbol ist erforderlich.",
        "report_desc": "Erstellen Sie die finalen Steuerwerte für die Anlage KAP für ein bestimmtes Konto und Jahr.",
        "err_no_acc_db": "Keine Konten in der Datenbank gefunden. Bitte importieren Sie zuerst IBKR-Daten.",
        "acc_multi_label": "IBKR Konto-ID(s)",
        "select_at_least_one": "Wählen Sie mindestens ein Konto aus.",
        "no_common_years": "Keine gemeinsamen Steuerjahre für diese Konten gefunden.",
        "tax_year_label": "Steuerjahr",
        "generating_report": "Erstelle Bericht für {}...",
        "missing_cost_msg": "Die folgenden Verkäufe haben keine entsprechenden Käufe. Dies führt zu einer falschen Berechnung (wird als 100% Gewinn gewertet, wenn nicht gelöst).",
        "prefill_btn": "📝 Prefill Manual",
        "prefill_success": "{} vorausgefüllt! Gehen Sie zum Tab **📝 Manuelle Positionen**.",
        "prefill_info": "💡 Sie können die Anschaffungskosten für diese Positionen im Tab **📝 Manuelle Positionen** erfassen und dann die FIFO-Engine neu starten.",
        "gen_anyway": "Bericht trotz fehlender Daten erstellen",
        "report_summary_comb": "Kombinierte Zusammenfassung ({})",
        "report_summary_single": "Zusammenfassung für {} ({})",
        "accounts_included": "📊 **Enthaltene Konten**: {}",
        "kap7_label": "KAP Zeile 7 (Dividenden / Zinsen / Ausgleich / Sonstiges)",
        "kap8_label": "KAP Zeile 8 (Aktien-Veräußerungsgewinne)",
        "kap9_label": "KAP Zeile 9 (Aktien-Veräußerungsverluste)",
        "kap10_label": "KAP Zeile 10 (Termingeschäfte Netto)",
        "kap10_gains": "  - davon Gewinne",
        "kap10_losses": "  - davon Verluste",
        "kap15_label": "KAP Zeile 15 (Quellensteuer)",
        "pool_summary_header": "Zusammenfassung nach Verlusttöpfen",
        "aktien_pool_label": "Aktientopf (Netto)",
        "allg_pool_label": "Allgemeiner Topf Ergebnis",
        "so_fx_total_label": "Anlage SO (FX Gesamt)",
        "so_header": "Anlage SO (§ 23 EStG Fremdwährungsgeschäfte)",
        "so_fx_gains_label": "SO FX Gesamtgewinn",
        "so_fx_taxable_label": "SO FX Steuerpflichtig (< 1 J.)",
        "so_fx_taxfree_label": "SO FX Steuerfrei (> 1 J.)",
        "freigrenze_applied": "ℹ️ **Freigrenze angewendet**: Da die privaten Veräußerungsgewinne (§ 23) unter 1.000 € liegen, bleiben diese steuerfrei.",
        "freigrenze_exceeded": "⚠️ **Freigrenze überschritten**: Gewinne ab 1.000 € sind voll steuerpflichtig.",
        "margin_header": "💰 Marginkosten (Info)",
        "margin_label": "Margin-Zinsen (Broker Interest Paid)",
        "margin_warning": """⚠️ **Nicht abzugsfähig**: Margin-Zinsen (Broker Interest Paid) stellen 
Werbungskosten dar, die gemäß § 20 Abs. 9 EStG nicht von Kapitalerträgen 
abgezogen werden dürfen. Dieser Betrag ist rein informativ und fließt 
**nicht** in die Berechnung der Anlage KAP ein. Details im Excel-Export 
auf dem Blatt **Marginkosten (Info)**.""",
        "individual_breakdowns": "Einzelkonto-Aufschlüsselung",
        "details_for": "📊 Details für {}",
        "what_do_lines_mean": "ℹ️ Was bedeuten diese Zeilen?",
        "table_header_line": "Zeile",
        "table_header_name": "Bezeichnung",
        "table_header_desc": "Erklärung",
        "line_7_name": "Kapitalerträge",
        "line_7_desc": "Dividenden, Zinsen, Ausgleichszahlungen und sonstige Gewinne (ETFs, Anleihen)",
        "line_8_name": "Gewinne Aktien",
        "line_8_desc": "Nur positive Gewinne aus Einzelaktien-Verkäufen",
        "line_9_name": "Verluste Aktien",
        "line_9_desc": "Aktienverluste (Absolutwert) — nur mit Aktiengewinnen verrechenbar",
        "line_10_name": "Termingeschäfte",
        "line_10_desc": "Netto-Ergebnis aus Optionen und Futures",
        "line_15_name": "Quellensteuer",
        "line_15_desc": "Anrechenbare ausländische Steuern (z.B. US-Withholding Tax)",
        "guide_footer": "> 📖 Ausführliche Erklärungen finden Sie im Tab **\"Tax Guide\"** und in der Datei `docs/GERMAN_TAX_THEORY.md`.",
        "export_header": "📥 Export nach Excel",
        "save_dialog_title": "Anlage KAP Bericht speichern",
        "export_success": "Bericht erfolgreich unter `{}` gespeichert!",
        "export_info": "Sie können die Datei nun in Excel öffnen.",
        "export_cancelled": "Speichervorgang abgebrochen.",
        "db_browser_header": "🗄️ Datenbank-Browser",
        "db_browser_desc": "Rohdaten direkt aus der SQLite-Datenbank einsehen.",
        "db_no_tables": "Keine Tabellen in der Datenbank gefunden.",
        "db_select_table": "Tabelle zur Ansicht wählen",
        "db_showing_data": "Daten für **{}** ({} Zeilen)",
        "guide_header": "📖 Steuer-Leitfaden für IBKR-Nutzer",
        "guide_desc": "Dieses Handbuch erklärt, wie IBKR2KAP Ihre Trades den Zeilen der **Anlage KAP** zuordnet und welche steuerlichen Regeln dabei angewendet werden.",
        "guide_lines_header": "📋 Anlage KAP — Zeilen im Überblick",
        "guide_pools_header": "⚖️ Verlusttöpfe (Tax Pools)",
        "guide_fifo_header": "🔢 FIFO-Prinzip (First-In-First-Out)",
        "guide_fx_header": "💱 Währungsumrechnung (FX)",
        "guide_ca_header": "🏢 Kapitalmaßnahmen (Corporate Actions)",
        "guide_opt_header": "📊 Optionen (Termingeschäfte)",
        "guide_disclaimer": "⚠️ **Haftungsausschluss**: Diese Informationen stellen keine Steuerberatung dar. Für individuelle steuerliche Fragen wenden Sie sich bitte an einen **Steuerberater**. Rechtsstand: 2024/2025 (JStG 2024).",
        "guide_full_ref": "📄 Die vollständige Referenz finden Sie in der Datei `docs/GERMAN_TAX_THEORY.md` im Projektverzeichnis.",
        "aktien_pool_explanation_info": "Aktienverluste können **nur** mit Aktiengewinnen verrechnet werden (§ 20 Abs. 6 Satz 5 EStG). Nicht verrechnete Verluste werden vorgetragen.",
    }
}

UI_TABS = {
    "en": ["📁 Data Import", "⚙️ Tax Processing", "📝 Manual Positions", "📊 Anlage KAP Report", "🗄️ Database Browser", "📖 Tax Guide"],
    "de": ["📁 Daten-Import", "⚙️ Steuer-Verarbeitung", "📝 Manuelle Positionen", "📊 Anlage KAP Bericht", "🗄️ Datenbank-Browser", "📖 Steuer-Leitfaden"]
}

# --- Page Config ---
st.set_page_config(
    page_title="IBKR2KAP — German Tax Assistant",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Hide Streamlit Menu and Deploy Button ---
st.markdown(
    """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display:none;}
    /* Force text to be highlightable everywhere */
    * {
        user-select: text !important;
        -webkit-user-select: text !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --- Database Initialization ---
@st.cache_resource
def init_connection():
    return get_engine()

engine = init_connection()
# Auto-migrate: create missing tables AND add missing columns on every startup.
# This MUST be outside @st.cache_resource so schema changes are always applied.
migrate_schema(engine, Base.metadata)
SessionLocal = get_session(engine)

# --- Sidebar ---
st.sidebar.title("IBKR2KAP")
lang = st.sidebar.selectbox("Language / Sprache", options=["en", "de"], index=1 if st.session_state.get("language") == "de" else 0)
st.session_state["language"] = lang
TR = UI_STRINGS[lang]
TABS_LIST = UI_TABS[lang]
CUR_KAP_TOOLTIPS = KAP_TOOLTIPS[lang]
CUR_TAX_POOL_EXPLANATIONS = TAX_POOL_EXPLANATIONS[lang]

st.sidebar.info(TR["sidebar_info"])

# --- Status Center (Persistent) ---
status_container = st.sidebar.container()
status_container.write("### " + TR["status_header"])
if "last_status" not in st.session_state:
    st.session_state["last_status"] = TR["status_ready"]
status_area = status_container.empty()
status_area.info(st.session_state["last_status"])

def update_status(msg, type="info"):
    st.session_state["last_status"] = msg
    if type == "info":
        status_area.info(msg)
    elif type == "success":
        status_area.success(msg)
    elif type == "warning":
        status_area.warning(msg)
    elif type == "error":
        status_area.error(msg)

# --- Main UI ---
st.title(TR["title"])

tabs = st.tabs(TABS_LIST)

# --- Tab 1: Data Import ---
with tabs[0]:
    st.header(TR["import_header"])
    st.markdown(TR["import_desc"])
    
    col1, col2 = st.columns(2)
    
    with col1:
        xml_files = st.file_uploader(TR["upload_xml"], type=["xml"], accept_multiple_files=True)
        if xml_files:
            if st.button(TR["btn_process_xml"]):
                for xml_file in xml_files:
                    update_status(TR["status_parsing"].format(xml_file.name))
                    with st.spinner(TR["status_parsing"].format(xml_file.name)):
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".xml") as tmp:
                            tmp.write(xml_file.getvalue())
                            tmp_path = tmp.name
                        
                        try:
                            with SessionLocal() as session:
                                results = run_import(tmp_path, session, file_type="xml")
                                session.commit()
                                update_status(TR["status_success"].format(xml_file.name), type="success")
                                st.success(TR["success_processed"].format(xml_file.name))
                                st.json(results["counts"])
                                
                                if results.get("warnings"):
                                    st.warning(TR["warning_unsupported"].format(xml_file.name))
                                    for warning in results["warnings"]:
                                        st.write(f"- **{warning['entity']}** (Account: {warning['account_id']}): {warning['message']}")
                        except Exception as e:
                            st.error(f"Error processing {xml_file.name}: {e}")
                        finally:
                            if os.path.exists(tmp_path):
                                os.remove(tmp_path)

    with col2:
        csv_files = st.file_uploader(TR["upload_csv"], type=["csv"], accept_multiple_files=True)
        if csv_files:
            if st.button(TR["btn_process_csv"]):
                for csv_file in csv_files:
                    update_status(TR["status_parsing"].format(csv_file.name))
                    with st.spinner(TR["status_parsing"].format(csv_file.name)):
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
                            tmp.write(csv_file.getvalue())
                            tmp_path = tmp.name
                        
                        try:
                            with SessionLocal() as session:
                                results = run_import(tmp_path, session, file_type="csv")
                                session.commit()
                                update_status(TR["status_success"].format(csv_file.name), type="success")
                                st.success(TR["success_processed"].format(csv_file.name))
                                st.json(results["counts"])
                                
                                if results.get("warnings"):
                                    st.warning(TR["warning_unsupported"].format(csv_file.name))
                                    for warning in results["warnings"]:
                                        st.write(f"- **{warning['entity']}** (Account: {warning.get('account_id', 'Unknown')}): {warning['message']}")
                        except Exception as e:
                            st.error(f"Error processing {csv_file.name}: {e}")
                        finally:
                            if os.path.exists(tmp_path):
                                os.remove(tmp_path)

    st.divider()
    with st.expander(TR["danger_zone"]):
        st.subheader(TR["reset_header"])
        st.warning(TR["reset_warning"])
        confirm = st.checkbox(TR["reset_confirm"])
        if st.button(TR["reset_btn"], disabled=not confirm):
            with st.spinner("Wiping data..."):
                try:
                    with SessionLocal() as session:
                        maint = MaintenanceService(session)
                        maint.reset_database()
                        st.success(TR["reset_success"])
                except Exception as e:
                    st.error(f"Error resetting database: {e}")

# --- Tab 2: Tax Processing (Placeholder for Plan 12.2) ---
with tabs[1]:
    st.header(TR["fifo_header"])
    st.markdown(TR["fifo_desc"])
    
    if st.button(TR["btn_run_fifo"]):
        with st.spinner(TR["fifo_running"]):
            try:
                update_status(TR["fifo_running"])
                with SessionLocal() as session:
                    runner = FIFORunner(session)
                    runner.run_all()
                    update_status(TR["fifo_complete"], type="success")
                    st.success(TR["fifo_complete"])
            except Exception as e:
                st.error(f"Error running FIFO: {e}")

# --- Tab 3: Manual Positions ---
with tabs[2]:
    st.header(TR["manual_header"])
    st.markdown(TR["manual_desc"])

    with SessionLocal() as session:
        mp_accounts = get_distinct_account_ids(session)

    if not mp_accounts:
        st.info(TR["no_accounts"])
    else:
        mp_account_id = st.selectbox(TR["account_label"], options=mp_accounts, key="mp_account_select")

        # Resolve internal DB id
        with SessionLocal() as session:
            mp_acc_db_id = session.execute(
                select(Account.id).where(Account.account_id == mp_account_id)
            ).scalar()

        if mp_acc_db_id is None:
            st.error(TR["account_not_found"])
        else:
            # --- Show existing manual positions ---
            with SessionLocal() as session:
                positions = get_manual_positions(session, mp_acc_db_id)

            if positions:
                st.subheader(TR["existing_manual"].format(len(positions)))
                rows = []
                for p in positions:
                    rows.append({
                        "ID": p.id,
                        "Symbol": p.symbol,
                        "B/S": p.buy_sell or "",
                        "Category": p.asset_category,
                        "Qty": float(p.quantity),
                        "Price": float(p.trade_price) if p.trade_price else None,
                        "Proceeds": float(p.proceeds) if p.proceeds else None,
                        "Comm": float(p.ib_commission) if p.ib_commission else None,
                        "Trading Costs": float(p.trading_costs_total) if p.trading_costs_total else 0.0,
                        "FX": float(p.fx_rate_to_base) if p.fx_rate_to_base else None,

                        "Date": p.acquisition_date,
                        "Desc": p.description,
                    })
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

                # Delete section
                with st.expander(TR["delete_manual_expander"]):
                    del_id = st.selectbox(
                        TR["delete_select_label"],
                        options=[p.id for p in positions],
                        format_func=lambda pid: next(
                            f"{p.symbol} — {p.quantity} @ {p.acquisition_date}" for p in positions if p.id == pid
                        ),
                        key="mp_delete_select",
                    )
                    if st.button(TR["delete_btn"], key="mp_delete_btn"):
                        with SessionLocal() as session:
                            deleted = delete_manual_position(session, del_id)
                        if deleted:
                            st.success(TR["delete_success"])
                            st.rerun()
                        else:
                            st.error(TR["delete_error"])
            else:
                st.info(TR["no_manual"])

            # --- Add form ---
            st.divider()
            st.subheader(TR["add_manual_header"])
            with st.form("add_manual_position_form", clear_on_submit=False):
                col_sym, col_cat, col_bs, col_oc = st.columns([2, 1, 1, 1])
                with col_sym:
                    mp_symbol = st.text_input(TR["symbol_label"], key="mp_symbol_input")
                with col_cat:
                    mp_asset_cat = st.selectbox(TR["asset_cat_label"], ["STK", "OPT", "FUT", "WAR"], key="mp_asset_cat")
                with col_bs:
                    mp_buy_sell = st.selectbox(TR["buy_sell_label"], ["BUY", "SELL"], key="mp_buy_sell")
                with col_oc:
                    mp_open_close = st.selectbox(TR["open_close_label"], ["O", "C"], key="mp_open_close")

                col_qty, col_price, col_curr, col_fx = st.columns(4)
                with col_qty:
                    mp_qty = st.number_input(TR["qty_label"], min_value=0.0001, step=1.0, format="%.4f", key="mp_qty_input")
                with col_price:
                    mp_price = st.number_input(TR["price_label"], min_value=0.0, step=0.01, format="%.4f", key="mp_price")
                with col_curr:
                    mp_currency = st.text_input(TR["currency_label"], value="USD", key="mp_currency")
                with col_fx:
                    mp_fx_rate = st.number_input(TR["fx_label"], min_value=0.0, value=1.0, step=0.0001, format="%.6f", key="mp_fx_rate")

                col_date, col_settle = st.columns(2)
                with col_date:
                    mp_trade_date = st.date_input(TR["trade_date_label"], key="mp_trade_date")
                with col_settle:
                    mp_settle_date = st.date_input(TR["settle_date_label"], key="mp_date_input")

                col_proceeds, col_comm, col_trcosts = st.columns(3)
                with col_proceeds:
                    mp_proceeds = st.number_input(TR["proceeds_label"], value=0.0, step=0.01, format="%.4f", key="mp_proceeds")
                with col_comm:
                    mp_comm = st.number_input(TR["comm_label"], value=0.0, step=0.01, format="%.4f", key="mp_comm")

                mp_desc = st.text_input(TR["desc_label"], value="", key="mp_desc")



                submitted = st.form_submit_button(TR["add_btn"])
                if submitted:
                    if not mp_symbol.strip():
                        st.error(TR["err_sym_req"])
                    else:
                        with SessionLocal() as session:
                            add_manual_position(
                                session,
                                mp_acc_db_id,
                                symbol=mp_symbol.strip().upper(),
                                asset_category=mp_asset_cat,
                                quantity=Decimal(str(mp_qty)),
                                acquisition_date=mp_settle_date.isoformat(),
                                trade_date=mp_trade_date.isoformat(),
                                cost_basis_total_eur=None,
                                description=mp_desc,
                                currency=mp_currency.upper(),
                                fx_rate_to_base=Decimal(str(mp_fx_rate)),
                                trade_price=Decimal(str(mp_price)),
                                proceeds=Decimal(str(mp_proceeds)),
                                taxes=Decimal("0"),
                                ib_commission=Decimal(str(mp_comm)),

                                buy_sell=mp_buy_sell,
                                open_close_indicator=mp_open_close,
                            )

                        # Clear prefill state after success
                        for key in [
                            "mp_symbol_input", "mp_asset_cat", "mp_buy_sell", "mp_open_close",
                            "mp_qty_input", "mp_price", "mp_currency", "mp_fx_rate",
                            "mp_trade_date", "mp_date_input", "mp_proceeds", "mp_comm", "mp_desc"
                        ]:
                            if key in st.session_state:
                                del st.session_state[key]
                        st.rerun()


# --- Tab 4: Anlage KAP Report ---
with tabs[3]:
    st.header(TR["report_header"])
    st.markdown(TR["report_desc"])
    # Fetch available accounts
    with SessionLocal() as session:
        available_accounts = get_distinct_account_ids(session)
    
    if not available_accounts:
        st.info(TR["err_no_acc_db"])
    else:
        col_acc, col_year = st.columns(2)
        with col_acc:
            default_acc = [available_accounts[0]] if available_accounts else []
            account_selection = st.multiselect(TR["acc_multi_label"], options=available_accounts, default=default_acc)
        
        # Fetch available years for the selected account(s)
        available_years = []
        if account_selection:
            with SessionLocal() as session:
                if len(account_selection) == 1:
                    available_years = get_tax_years_for_account(session, account_selection[0])
                else:
                    # In combined mode, show only years that are available in ALL selected accounts
                    year_sets = []
                    for acc in account_selection:
                        year_sets.append(set(get_tax_years_for_account(session, acc)))
                    if year_sets:
                        intersected = year_sets[0]
                        for s in year_sets[1:]:
                            intersected = intersected.intersection(s)
                        available_years = sorted(list(intersected), reverse=True)
        
        with col_year:
            if not account_selection:
                st.info(TR["select_at_least_one"])
                tax_year = None
            elif not available_years:
                st.warning(TR["no_common_years"])
                tax_year = None
            else:
                tax_year = st.selectbox(TR["tax_year_label"], options=available_years)
        
        if tax_year and st.button(TR["btn_gen_report"]):
            st.session_state["report_accounts"] = account_selection
            st.session_state["report_year"] = tax_year
            update_status(TR["generating_report"].format(tax_year))

        if st.session_state.get("report_accounts") == account_selection and st.session_state.get("report_year") == tax_year:
            with st.spinner("Aggregating tax data..."):
                try:
                    with SessionLocal() as session:
                        aggregator = TaxAggregatorService(session)
                        is_combined = len(account_selection) > 1
                        
                        if is_combined:
                            report = aggregator.generate_combined_report(account_selection, tax_year)
                        else:
                            report = aggregator.generate_report(account_selection[0], tax_year)
                        
                        # Check for warnings
                        can_show_report = True
                        
                        def set_prefill_state(sym, cat, q, dt_str):
                            from datetime import date
                            st.session_state["mp_symbol_input"] = sym
                            st.session_state["mp_asset_cat"] = cat
                            st.session_state["mp_qty_input"] = float(abs(q))
                            st.session_state["mp_date_input"] = date.fromisoformat(dt_str)
                            st.session_state["mp_trade_date"] = date.fromisoformat(dt_str)
                            # Smart prefill: if we miss an opening for a SELL, prefill BUY + Open
                            st.session_state["mp_buy_sell"] = "BUY"
                            st.session_state["mp_open_close"] = "O"
                            # Also set defaults for other fields to ensure they are clean
                            st.session_state["mp_price"] = 0.0
                            st.session_state["mp_currency"] = "USD"
                            st.session_state["mp_fx_rate"] = 1.0
                            st.session_state["mp_proceeds"] = 0.0
                            st.session_state["mp_comm"] = 0.0
                            st.session_state["mp_desc"] = f"Manual cost basis for {sym}"
                            update_status(f"Prefilled {sym}")

                        if report.missing_cost_basis_warnings:
                            st.warning(TR["missing_cost_warning"])
                            st.error(TR["missing_cost_msg"])
                            for warning in report.missing_cost_basis_warnings:
                                w_col1, w_col2 = st.columns([4, 1])
                                with w_col1:
                                    # Use st.code so the user instantly gets a copy button next to the text
                                    st.code(warning.message, language="markdown")
                                with w_col2:
                                    if st.button(TR["prefill_btn"], key=f"prefill_{warning.trade_id}_{warning.symbol}_{warning.date}", on_click=set_prefill_state, args=(warning.symbol, warning.asset_category, warning.quantity, warning.date)):
                                        st.success(TR["prefill_success"].format(warning.symbol))
                            
                            st.info(TR["prefill_info"])
                            
                            if not st.checkbox(TR["gen_anyway"]):
                                can_show_report = False
                        
                        if can_show_report:
                            # Display Metrics
                            if is_combined:
                                report_title = TR["report_summary_comb"].format(tax_year)
                            else:
                                report_title = TR["report_summary_single"].format(account_selection[0], tax_year)
                                
                            st.subheader(report_title)
                            
                            if is_combined:
                                st.info(TR["accounts_included"].format(', '.join(account_selection)))
                            m1, m2, m3 = st.columns(3)
                            m1.metric(TR["kap7_label"], f"{report.kap_line_7_kapitalertraege:,.2f} €", help=CUR_KAP_TOOLTIPS["kap_line_7"])
                            m2.metric(TR["kap8_label"], f"{report.kap_line_8_gewinne_aktien:,.2f} €", help=CUR_KAP_TOOLTIPS["kap_line_8"])
                            m3.metric(TR["kap9_label"], f"{report.kap_line_9_verluste_aktien:,.2f} €", help=CUR_KAP_TOOLTIPS["kap_line_9"])
                            
                            m4, m5, m6 = st.columns(3)
                            m4.metric(TR["kap10_label"], f"{report.kap_line_10_termingeschaefte:,.2f} €", help=CUR_KAP_TOOLTIPS["kap_line_10"])
                            m5.metric(TR["kap10_gains"], f"{report.kap_termingeschaefte_gains:,.2f} €")
                            m6.metric(TR["kap10_losses"], f"{report.kap_termingeschaefte_losses:,.2f} €")
                            
                            st.metric(TR["kap15_label"], f"{report.kap_line_15_quellensteuer:,.2f} €", help=CUR_KAP_TOOLTIPS["kap_line_15"])
                            
                            st.divider()
                            st.subheader(TR["pool_summary_header"])
                            z1, z2, z3 = st.columns(3)
                            z1.metric(TR["aktien_pool_label"], f"{report.aktien_net_result:,.2f} €", help=CUR_KAP_TOOLTIPS["aktien_net_result"])
                            z2.metric(TR["allg_pool_label"], f"{report.allgemeiner_topf_result:,.2f} €", help=CUR_KAP_TOOLTIPS["allgemeiner_topf_result"])
                            # Exploded view for Termingeschäfte in pool summary if desired, 
                            # but we already show it above. Keeping it simple here.
                            z3.metric(TR["so_fx_total_label"], f"{report.so_fx_gains_total:,.2f} €", help="Summe aller Währungsgewinne (Anlage SO).")
                            
                            st.subheader(TR["so_header"])
                            s1, s2, s3 = st.columns(3)
                            s1.metric(TR["so_fx_gains_label"], f"{report.so_fx_gains_total:,.2f} €")
                            s2.metric(TR["so_fx_taxable_label"], f"{report.so_fx_gains_taxable_1y:,.2f} €")
                            s3.metric(TR["so_fx_taxfree_label"], f"{report.so_fx_gains_tax_free:,.2f} €")

                            if report.so_fx_freigrenze_applies:
                                st.info(TR["freigrenze_applied"])
                            elif report.so_fx_gains_taxable_1y >= 1000:
                                st.warning(TR["freigrenze_exceeded"])

                            # Margin Interest (informational)
                            if report.margin_interest_paid > 0:
                                st.subheader(TR["margin_header"])
                                st.metric(
                                    TR["margin_label"],
                                    f"{report.margin_interest_paid:,.2f} €",
                                    help="Nicht in Anlage KAP enthalten — Marginzinsen sind gemäß § 20 Abs. 9 EStG nicht als Werbungskosten abzugsfähig."
                                )
                                st.warning(TR["margin_warning"])

                            if is_combined:
                                st.divider()
                                st.subheader(TR["individual_breakdowns"])
                                for acc_rep in report.per_account_reports:
                                    with st.expander(TR["details_for"].format(acc_rep.account_id)):
                                        am1, am2, am3 = st.columns(3)
                                        am1.metric("KAP 7", f"{acc_rep.kap_line_7_kapitalertraege:,.2f} €")
                                        am2.metric("KAP 8", f"{acc_rep.kap_line_8_gewinne_aktien:,.2f} €")
                                        am3.metric("KAP 9", f"{acc_rep.kap_line_9_verluste_aktien:,.2f} €")
                                        
                                        am4, am5, am6 = st.columns(3)
                                        am4.metric("KAP 10 Netto", f"{acc_rep.kap_line_10_termingeschaefte:,.2f} €")
                                        am5.metric("KAP 10 Gewinne", f"{acc_rep.kap_termingeschaefte_gains:,.2f} €")
                                        am6.metric("KAP 10 Verluste", f"{acc_rep.kap_termingeschaefte_losses:,.2f} €")
                                        st.metric("SO FX", f"{acc_rep.so_fx_gains_total:,.2f} €")

                            with st.expander(TR["what_do_lines_mean"]):
                                st.markdown(
                                    f"| {TR['table_header_line']} | {TR['table_header_name']} | {TR['table_header_desc']} |\n"
                                    "|---|---|---|\n"
                                    f"| **7** | {TR['line_7_name']} | {TR['line_7_desc']} |\n"
                                    f"| **8** | {TR['line_8_name']} | {TR['line_8_desc']} |\n"
                                    f"| **9** | {TR['line_9_name']} | {TR['line_9_desc']} |\n"
                                    f"| **10** | {TR['line_10_name']} | {TR['line_10_desc']} |\n"
                                    f"| **15** | {TR['line_15_name']} | {TR['line_15_desc']} |\n"
                                    "\n"
                                    f"{TR['guide_footer']}"
                                )
                            st.divider()
                            st.subheader(TR["export_header"])
                            
                            exporter = ExcelExportService(session)
                            
                            if is_combined:
                                fname = f"Anlage_KAP_Combined_{tax_year}.xlsx"
                            else:
                                fname = f"Anlage_KAP_{account_selection[0]}_{tax_year}.xlsx"
                            
                            if st.button(TR["save_btn"], type="primary"):
                                import tkinter as tk
                                from tkinter import filedialog
                                
                                # Use Tkinter to show a native OS Save Dialog. 
                                # This bypasses all problematic browser download managers!
                                root = tk.Tk()
                                root.withdraw()
                                root.wm_attributes('-topmost', 1)
                                
                                save_path = filedialog.asksaveasfilename(
                                    initialfile=fname,
                                    defaultextension=".xlsx",
                                    filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
                                    title=TR["save_dialog_title"]
                                )
                                root.destroy()
                                
                                if save_path:
                                    if is_combined:
                                        exporter.export_combined(report, save_path, lang=lang)
                                    else:
                                        exporter.export(report, save_path, lang=lang)
                                    st.success(TR["export_success"].format(save_path))
                                    st.info(TR["export_info"])
                                else:
                                    st.warning(TR["export_cancelled"])
                        
                except Exception as e:
                    st.error(f"Error generating report: {e}")

# --- Tab 5: Database Browser ---
with tabs[4]:
    st.header(TR["db_browser_header"])
    st.markdown(TR["db_browser_desc"])
    
    try:
        # Fetch all table names
        query_tables = "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
        tables_df = pd.read_sql(query_tables, con=engine)
        table_names = sorted(tables_df["name"].tolist())
        
        if not table_names:
            st.info(TR["db_no_tables"])
        else:
            selected_table = st.selectbox(TR["db_select_table"], table_names)
            
            if selected_table:
                col_ctrl1, col_ctrl2 = st.columns([1, 4])
                # We don't strictly need a refresh button as Streamlit reruns on change, 
                # but a button can force it if using caching.
                
                # Fetch row count
                count_df = pd.read_sql(f'SELECT count(*) as count FROM "{selected_table}"', con=engine)
                row_count = count_df["count"][0]
                st.write(TR["db_showing_data"].format(selected_table, row_count))
                
                # Load data (using limited load if too big, but for now full load)
                df = pd.read_sql(f'SELECT * FROM "{selected_table}"', con=engine)
                st.dataframe(df, use_container_width=True)
                
    except Exception as e:
        st.error(f"Error browsing database: {e}")

# --- Tab 6: Tax Guide ---
with tabs[5]:
    st.header(TR["guide_header"])
    st.markdown(TR["guide_desc"])
    
    with st.expander(TR["guide_lines_header"], expanded=True):
        st.markdown(
            f"**{TR['table_header_line']} 7 — {TR['line_7_name']}**\n\n"
            f"{TR['line_7_desc']}.\n\n"
            f"**{TR['table_header_line']} 8 — {TR['line_8_name']}**\n\n"
            f"{TR['line_8_desc']}.\n\n"
            f"**{TR['table_header_line']} 9 — {TR['line_9_name']}**\n\n"
            f"{TR['line_9_desc']}.\n\n"
            f"**{TR['table_header_line']} 10 — {TR['line_10_name']}**\n\n"
            f"{TR['line_10_desc']}.\n\n"
            f"**{TR['table_header_line']} 15 — {TR['line_15_name']}**\n\n"
            f"{TR['line_15_desc']}."
        )
    
    with st.expander(TR["guide_pools_header"]):
        for pool_name, explanation in CUR_TAX_POOL_EXPLANATIONS.items():
            st.markdown(f"**{pool_name}**: {explanation}")
        st.info(TR["aktien_pool_explanation_info"])
    
    with st.expander(TR["guide_fifo_header"]):
        if lang == "de":
            st.markdown(
                "Bei der Berechnung des Veräußerungsgewinns wird unterstellt, dass die **zuerst angeschafften** "
                "Wertpapiere auch **zuerst veräußert** werden (§ 20 Abs. 4 Satz 7 EStG).\n\n"
                "IBKR2KAP verwendet das **Settlement-Datum** (Valuta) für die steuerliche Zuordnung:\n"
                "- Bei Aktien liegt das Settlement i. d. R. **T+2** (zwei Geschäftstage nach dem Handelstag)\n"
                "- Ein Trade am 30.12.2023 mit Settlement am 03.01.2024 gehört steuerlich ins **Jahr 2024**"
            )
        else:
            st.markdown(
                "When calculating the capital gain, it is assumed that the **first acquired** "
                "securities are also **first sold** (§ 20 Abs. 4 Sentence 7 EStG).\n\n"
                "IBKR2KAP uses the **settlement date** (valuta) for tax allocation:\n"
                "- For stocks, settlement is usually **T+2** (two business days after the trade date)\n"
                "- A trade on 2023-12-30 with settlement on 2024-01-03 belongs to the **tax year 2024**"
            )
    
    with st.expander(TR["guide_fx_header"]):
        if lang == "de":
            st.markdown(
                "**ECB-Referenzkurse**: Alle Fremdwährungsbeträge werden zum offiziellen EZB-Kurs in Euro "
                "umgerechnet. An Wochenenden/Feiertagen wird der letzte verfügbare Geschäftstagskurs verwendet.\n\n"
                "**FX-Gewinne (§ 23 EStG)**: Gewinne aus dem Halten von Fremdwährung sind steuerpflichtig, "
                "wenn die Haltefrist unter einem Jahr liegt. Diese gehören in die **Anlage SO**, nicht in die Anlage KAP. "
                "IBKR2KAP berechnet die Haltefrist automatisch per FIFO."
            )
        else:
            st.markdown(
                "**ECB Reference Rates**: All foreign currency amounts are converted into Euro at the official ECB rate. "
                "On weekends/holidays, the last available business day rate is used.\n\n"
                "**FX Gains (§ 23 EStG)**: Gains from holding foreign currency are taxable if the holding period is less than one year. "
                "These belong to **Anlage SO**, not Anlage KAP. IBKR2KAP calculates the holding period automatically via FIFO."
            )
    
    with st.expander(TR["guide_ca_header"]):
        if lang == "de":
            st.markdown(
                "- **Aktiensplits**: Kein steuerpflichtiger Vorgang. Anschaffungskosten werden über den "
                "Splitfaktor auf die neue Stückzahl verteilt.\n"
                "- **Reverse Splits**: Ebenfalls steuerneutral. Kosten werden konsolidiert, "
                "auch bei Symbol-/ISIN-Änderung.\n"
                "- **Spinoffs**: Anschaffungskosten der Mutteraktie werden anteilig auf Mutter und "
                "Tochter aufgeteilt. Erst beim späteren Verkauf wird der anteilige Gewinn realisiert."
            )
        else:
            st.markdown(
                "- **Stock Splits**: Not a taxable event. Acquisition costs are distributed over the new quantity via the split factor.\n"
                "- **Reverse Splits**: Also tax-neutral. Costs are consolidated, even with symbol/ISIN changes.\n"
                "- **Spinoffs**: Acquisition costs of the parent stock are proportionally divided between parent and subsidiary. "
                "The proportional gain is only realized upon later sale."
            )
    
    with st.expander(TR["guide_opt_header"]):
        if lang == "de":
            st.markdown(
                "| Situation | Steuerliche Behandlung |\n"
                "|---|---|\n"
                "| **Verfall (Expiry)** | Prämie wird als Gewinn oder Verlust realisiert |\n"
                "| **Ausübung (Exercise)** | Prämie fließt in die Anschaffungskosten der Aktie — kein separater Gewinn/Verlust |\n"
                "| **Zuteilung (Assignment)** | Wie Ausübung — Prämie passt die Cost Basis der Aktie an |\n"
                "\n"
                "Optionen werden als **Termingeschäfte** kategorisiert und in **Zeile 10** erfasst."
            )
        else:
            st.markdown(
                "| Situation | Tax Treatment |\n"
                "|---|---|\n"
                "| **Expiry** | Premium is realized as gain or loss |\n"
                "| **Exercise** | Premium flows into the acquisition cost of the stock — no separate gain/loss |\n"
                "| **Assignment** | Like exercise — premium adjusts the cost basis of the stock |\n"
                "\n"
                "Options are categorized as **derivatives** and recorded in **Line 10**."
            )
    
    st.divider()
    st.warning(TR["guide_disclaimer"])
    st.info(TR["guide_full_ref"])
