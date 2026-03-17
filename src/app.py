import streamlit as st
import tempfile
import os
from sqlalchemy.orm import Session
from ibkr_tax.db.engine import get_engine, get_session
from ibkr_tax.models.database import Base
from ibkr_tax.services.pipeline import run_import
from ibkr_tax.services.fifo_runner import FIFORunner
from ibkr_tax.services.tax_aggregator import TaxAggregatorService
from ibkr_tax.services.maintenance import MaintenanceService
from ibkr_tax.services.excel_export import ExcelExportService
from ibkr_tax.db.repository import get_distinct_account_ids, get_tax_years_for_account
from ibkr_tax.services.tax_tooltips import KAP_TOOLTIPS, TAX_POOL_EXPLANATIONS

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
    </style>
    """,
    unsafe_allow_html=True
)

# --- Database Initialization ---
@st.cache_resource
def init_connection():
    engine = get_engine()
    # Ensure tables are created (idempotent)
    Base.metadata.create_all(bind=engine)
    return engine

engine = init_connection()
SessionLocal = get_session(engine)

# --- Sidebar ---
st.sidebar.title("IBKR2KAP")
st.sidebar.info("Local-first tax assistant for German IBKR users.")

# --- Main UI ---
st.title("🛡️ IBKR2KAP — Tax Reporting")

tabs = st.tabs(["📁 Data Import", "⚙️ Tax Processing", "📊 Anlage KAP Report", "🗄️ Database Browser", "📖 Tax Guide"])

# --- Tab 1: Data Import ---
with tabs[0]:
    st.header("Import IBKR Data")
    st.markdown("""
    Upload your **Flex Query XML** or **Activity Statement CSV** files here.
    Data is stored locally in your SQLite database.
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        xml_file = st.file_uploader("Upload Flex XML", type=["xml"])
        if xml_file:
            if st.button("Process XML"):
                with st.spinner("Parsing XML..."):
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".xml") as tmp:
                        tmp.write(xml_file.getvalue())
                        tmp_path = tmp.name
                    
                    try:
                        with SessionLocal() as session:
                            results = run_import(tmp_path, session, file_type="xml")
                            session.commit()
                            st.success(f"Successfully processed {xml_file.name}")
                            st.json(results["counts"])
                            
                            if results.get("warnings"):
                                st.warning("⚠️ **Unsupported Data Entities Found**")
                                for warning in results["warnings"]:
                                    st.write(f"- **{warning['entity']}** (Account: {warning['account_id']}): {warning['message']}")
                                st.info("Note: The data above was skipped as there is currently no handling for these record types in this version of the app.")
                    except Exception as e:
                        st.error(f"Error processing XML: {e}")
                    finally:
                        if os.path.exists(tmp_path):
                            os.remove(tmp_path)

    with col2:
        csv_file = st.file_uploader("Upload Activity CSV (Fallback)", type=["csv"])
        if csv_file:
            if st.button("Process CSV"):
                with st.spinner("Parsing CSV..."):
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
                        tmp.write(csv_file.getvalue())
                        tmp_path = tmp.name
                    
                    try:
                        with SessionLocal() as session:
                            results = run_import(tmp_path, session, file_type="csv")
                            session.commit()
                            st.success(f"Successfully processed {csv_file.name}")
                            st.json(results["counts"])
                            
                            if results.get("warnings"):
                                st.warning("⚠️ **Unsupported Data Entities Found**")
                                for warning in results["warnings"]:
                                    st.write(f"- **{warning['entity']}** (Account: {warning.get('account_id', 'Unknown')}): {warning['message']}")
                    except Exception as e:
                        st.error(f"Error processing CSV: {e}")
                    finally:
                        if os.path.exists(tmp_path):
                            os.remove(tmp_path)

    st.divider()
    with st.expander("🚨 Dangerous Zone"):
        st.subheader("Reset All Data")
        st.warning("This will permanently delete all trades, cash transactions, and processed results. Only account IDs will be preserved.")
        confirm = st.checkbox("I understand that this action is irreversible")
        if st.button("🚨 Reset Database", disabled=not confirm):
            with st.spinner("Wiping data..."):
                try:
                    with SessionLocal() as session:
                        maint = MaintenanceService(session)
                        maint.reset_database()
                        st.success("Database has been reset. All transaction tables are now empty.")
                except Exception as e:
                    st.error(f"Error resetting database: {e}")

# --- Tab 2: Tax Processing (Placeholder for Plan 12.2) ---
with tabs[1]:
    st.header("FIFO Matching & Tax Allocation")
    st.markdown("""
    Run the FIFO matching engine to calculate realized gains and losses across all accounts.
    This process:
    1. Clears existing FIFO matches for all accounts.
    2. Matches Sell trades against Buy lots in FIFO order.
    3. Allocates results to German tax pools (Aktien vs. Termingeschäfte).
    """)
    
    if st.button("🚀 Run FIFO Engine (All Accounts)"):
        with st.spinner("Executing FIFO logic..."):
            try:
                with SessionLocal() as session:
                    runner = FIFORunner(session)
                    runner.run_all()
                    st.success("FIFO calculation complete for all accounts!")
            except Exception as e:
                st.error(f"Error running FIFO: {e}")

# --- Tab 3: Anlage KAP Report (Placeholder for Plan 12.2) ---
with tabs[2]:
    st.header("Anlage KAP Generation")
    st.markdown("Generate the final tax report figures for a specific account and year.")
    # Fetch available accounts
    with SessionLocal() as session:
        available_accounts = get_distinct_account_ids(session)
    
    if not available_accounts:
        st.info("No accounts found in the database. Please import some IBKR data first.")
    else:
        col_acc, col_year = st.columns(2)
        with col_acc:
            account_id = st.selectbox("IBKR Account ID", options=available_accounts)
        
        # Fetch available years for the selected account
        with SessionLocal() as session:
            available_years = get_tax_years_for_account(session, account_id)
        
        with col_year:
            if not available_years:
                st.warning("No tax data found for this account.")
                tax_year = None
            else:
                tax_year = st.selectbox("Tax Year", options=available_years)
        
        if tax_year and st.button("📊 Generate Tax Report"):
            with st.spinner("Aggregating tax data..."):
                try:
                    with SessionLocal() as session:
                        aggregator = TaxAggregatorService(session)
                        report = aggregator.generate_report(account_id, tax_year)
                        
                        # Check for warnings
                        can_show_report = True
                        if report.missing_cost_basis_warnings:
                            st.warning("⚠️ **Missing Cost Basis Detected**")
                            st.error("The following sell trades do not have corresponding buy trades. This will lead to an incorrect taxable gain/loss calculation (treated as 100% gain if not resolved).")
                            for warning in report.missing_cost_basis_warnings:
                                st.write(f"- {warning}")
                            
                            st.info("💡 To fix this, you may need to import historical data from previous years or manually adjust lots.")
                            
                            if not st.checkbox("Generate report anyway despite missing data"):
                                can_show_report = False
                        
                        if can_show_report:
                            # Display Metrics
                            st.subheader(f"Report Summary for {account_id} ({tax_year})")
                            m1, m2, m3 = st.columns(3)
                            m1.metric("KAP Line 7 (Kapitalerträge)", f"{report.kap_line_7_kapitalertraege:,.2f} €", help=KAP_TOOLTIPS["kap_line_7"])
                            m2.metric("KAP Line 8 (Gewinne Aktien)", f"{report.kap_line_8_gewinne_aktien:,.2f} €", help=KAP_TOOLTIPS["kap_line_8"])
                            m3.metric("KAP Line 9 (Verluste Aktien)", f"{report.kap_line_9_verluste_aktien:,.2f} €", help=KAP_TOOLTIPS["kap_line_9"])
                            
                            m4, m5, m6 = st.columns(3)
                            m4.metric("KAP Line 10 (Termingeschäfte)", f"{report.kap_line_10_termingeschaefte:,.2f} €", help=KAP_TOOLTIPS["kap_line_10"])
                            m5.metric("KAP Line 15 (Quellensteuer)", f"{report.kap_line_15_quellensteuer:,.2f} €", help=KAP_TOOLTIPS["kap_line_15"])
                            m6.metric("Total Realized PnL", f"{report.total_realized_pnl:,.2f} €", help=KAP_TOOLTIPS["total_realized_pnl"])
                            
                            with st.expander("ℹ️ Was bedeuten diese Zeilen?"):
                                st.markdown(
                                    "| Zeile | Bezeichnung | Erklärung |\n"
                                    "|---|---|---|\n"
                                    "| **7** | Kapitalerträge | Dividenden, Zinsen und sonstige Gewinne (ETFs, Anleihen) |\n"
                                    "| **8** | Gewinne Aktien | Nur positive Gewinne aus Einzelaktien-Verkäufen |\n"
                                    "| **9** | Verluste Aktien | Aktienverluste (Absolutwert) — nur mit Aktiengewinnen verrechenbar |\n"
                                    "| **10** | Termingeschäfte | Netto-Ergebnis aus Optionen und Futures |\n"
                                    "| **15** | Quellensteuer | Ausländische Steuern — anrechenbar auf die deutsche Steuer |\n"
                                    "\n"
                                    '> 📖 Ausführliche Erklärungen finden Sie im Tab **"Tax Guide"** und in der Datei `docs/GERMAN_TAX_THEORY.md`.'
                                )
                            
                            # Excel Export
                            st.divider()
                            st.subheader("📥 Export to Excel")
                            
                            exporter = ExcelExportService(session)
                            with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
                                tmp_path = tmp.name
                            
                            exporter.export(report, tmp_path)
                            
                            with open(tmp_path, "rb") as f:
                                btn = st.download_button(
                                    label="Download Anlage KAP Excel Report",
                                    data=f,
                                    file_name=f"Anlage_KAP_{account_id}_{tax_year}.xlsx",
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                                )
                            
                            os.remove(tmp_path)
                        
                except Exception as e:
                    st.error(f"Error generating report: {e}")

# --- Tab 4: Database Browser ---
with tabs[3]:
    import pandas as pd
    st.header("🗄️ Database Browser")
    st.markdown("Inspect raw data directly from the SQLite database.")
    
    try:
        # Fetch all table names
        query_tables = "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
        tables_df = pd.read_sql(query_tables, con=engine)
        table_names = sorted(tables_df["name"].tolist())
        
        if not table_names:
            st.info("No tables found in the database.")
        else:
            selected_table = st.selectbox("Select Table to Inspect", table_names)
            
            if selected_table:
                col_ctrl1, col_ctrl2 = st.columns([1, 4])
                # We don't strictly need a refresh button as Streamlit reruns on change, 
                # but a button can force it if using caching.
                
                # Fetch row count
                count_df = pd.read_sql(f'SELECT count(*) as count FROM "{selected_table}"', con=engine)
                row_count = count_df["count"][0]
                st.write(f"Showing data for **{selected_table}** ({row_count} rows)")
                
                # Load data (using limited load if too big, but for now full load)
                df = pd.read_sql(f'SELECT * FROM "{selected_table}"', con=engine)
                st.dataframe(df, use_container_width=True)
                
    except Exception as e:
        st.error(f"Error browsing database: {e}")

# --- Tab 5: Tax Guide ---
with tabs[4]:
    st.header("📖 German Tax Guide for IBKR Users")
    st.markdown(
        "Dieses Handbuch erklärt, wie IBKR2KAP Ihre Trades den Zeilen der "
        "**Anlage KAP** zuordnet und welche steuerlichen Regeln dabei angewendet werden."
    )
    
    with st.expander("📋 Anlage KAP — Zeilen im Überblick", expanded=True):
        st.markdown(
            "**Zeile 7 — Kapitalerträge (allgemein)**\n\n"
            "Dividenden, Zinsen und Gewinne/Verluste aus sonstigen Wertpapieren (ETFs, Anleihen, Fonds). "
            "Aktiengewinne und Termingeschäfte werden separat erfasst.\n\n"
            "**Zeile 8 — Gewinne aus Aktienveräußerungen**\n\n"
            "Nur die positiven realisierten Gewinne aus dem Verkauf von Einzelaktien. "
            "ETFs gelten steuerlich nicht als Aktien.\n\n"
            "**Zeile 9 — Verluste aus Aktienveräußerungen**\n\n"
            "Absolutwert der Aktienverluste. Diese Verluste dürfen ausschließlich mit Aktiengewinnen "
            "(Zeile 8) verrechnet werden — nicht mit Dividenden oder sonstigen Erträgen.\n\n"
            "**Zeile 10 — Termingeschäfte (netto)**\n\n"
            "Gewinne minus Verluste aus Optionen und Futures. "
            "Die 20.000 €-Verlustbegrenzung wurde durch das JStG 2024 rückwirkend aufgehoben.\n\n"
            "**Zeile 15 — Anrechenbare ausländische Steuern**\n\n"
            "Im Ausland einbehaltene Quellensteuern auf Dividenden und Zinsen. "
            "Diese können auf die deutsche Abgeltungsteuer angerechnet werden."
        )
    
    with st.expander("⚖️ Verlusttöpfe (Tax Pools)"):
        for pool_name, explanation in TAX_POOL_EXPLANATIONS.items():
            st.markdown(f"**{pool_name}**: {explanation}")
        st.info(
            "Aktienverluste können **nur** mit Aktiengewinnen verrechnet werden "
            "(§ 20 Abs. 6 Satz 5 EStG). Nicht verrechnete Verluste werden vorgetragen."
        )
    
    with st.expander("🔢 FIFO-Prinzip (First-In-First-Out)"):
        st.markdown(
            "Bei der Berechnung des Veräußerungsgewinns wird unterstellt, dass die **zuerst angeschafften** "
            "Wertpapiere auch **zuerst veräußert** werden (§ 20 Abs. 4 Satz 7 EStG).\n\n"
            "IBKR2KAP verwendet das **Settlement-Datum** (Valuta) für die steuerliche Zuordnung:\n"
            "- Bei Aktien liegt das Settlement i. d. R. **T+2** (zwei Geschäftstage nach dem Handelstag)\n"
            "- Ein Trade am 30.12.2023 mit Settlement am 03.01.2024 gehört steuerlich ins **Jahr 2024**"
        )
    
    with st.expander("💱 Währungsumrechnung (FX)"):
        st.markdown(
            "**ECB-Referenzkurse**: Alle Fremdwährungsbeträge werden zum offiziellen EZB-Kurs in Euro "
            "umgerechnet. An Wochenenden/Feiertagen wird der letzte verfügbare Geschäftstagskurs verwendet.\n\n"
            "**FX-Gewinne (§ 23 EStG)**: Gewinne aus dem Halten von Fremdwährung sind steuerpflichtig, "
            "wenn die Haltefrist unter einem Jahr liegt. Diese gehören in die **Anlage SO**, nicht in die Anlage KAP. "
            "IBKR2KAP berechnet die Haltefrist automatisch per FIFO."
        )
    
    with st.expander("🏢 Kapitalmaßnahmen (Corporate Actions)"):
        st.markdown(
            "- **Aktiensplits**: Kein steuerpflichtiger Vorgang. Anschaffungskosten werden über den "
            "Splitfaktor auf die neue Stückzahl verteilt.\n"
            "- **Reverse Splits**: Ebenfalls steuerneutral. Kosten werden konsolidiert, "
            "auch bei Symbol-/ISIN-Änderung.\n"
            "- **Spinoffs**: Anschaffungskosten der Mutteraktie werden anteilig auf Mutter und "
            "Tochter aufgeteilt. Erst beim späteren Verkauf wird der anteilige Gewinn realisiert."
        )
    
    with st.expander("📊 Optionen (Termingeschäfte)"):
        st.markdown(
            "| Situation | Steuerliche Behandlung |\n"
            "|---|---|\n"
            "| **Verfall (Expiry)** | Prämie wird als Gewinn oder Verlust realisiert |\n"
            "| **Ausübung (Exercise)** | Prämie fließt in die Anschaffungskosten der Aktie — kein separater Gewinn/Verlust |\n"
            "| **Zuteilung (Assignment)** | Wie Ausübung — Prämie passt die Cost Basis der Aktie an |\n"
            "\n"
            "Optionen werden als **Termingeschäfte** kategorisiert und in **Zeile 10** erfasst."
        )
    
    st.divider()
    st.warning(
        "⚠️ **Haftungsausschluss**: Diese Informationen stellen keine Steuerberatung dar. "
        "Für individuelle steuerliche Fragen wenden Sie sich bitte an einen **Steuerberater**. "
        "Rechtsstand: 2024/2025 (JStG 2024)."
    )
    st.info("📄 Die vollständige Referenz finden Sie in der Datei `docs/GERMAN_TAX_THEORY.md` im Projektverzeichnis.")
