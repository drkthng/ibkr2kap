import streamlit as st
import tempfile
import os
from sqlalchemy.orm import Session
from ibkr_tax.db.engine import get_engine, get_session
from ibkr_tax.models.database import Base
from ibkr_tax.services.pipeline import run_import
from ibkr_tax.services.fifo_runner import FIFORunner
from ibkr_tax.services.tax_aggregator import TaxAggregatorService
from ibkr_tax.services.excel_export import ExcelExportService

# --- Page Config ---
st.set_page_config(
    page_title="IBKR2KAP — German Tax Assistant",
    layout="wide",
    initial_sidebar_state="expanded"
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

tabs = st.tabs(["📁 Data Import", "⚙️ Tax Processing", "📊 Anlage KAP Report"])

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
                    except Exception as e:
                        st.error(f"Error processing CSV: {e}")
                    finally:
                        if os.path.exists(tmp_path):
                            os.remove(tmp_path)

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
    
    col_acc, col_year = st.columns(2)
    with col_acc:
        account_id = st.text_input("IBKR Account ID", placeholder="e.g. U1234567")
    with col_year:
        tax_year = st.number_input("Tax Year", min_value=2020, max_value=2030, value=2024)
    
    if st.button("📊 Generate Tax Report"):
        if not account_id:
            st.warning("Please enter an Account ID.")
        else:
            with st.spinner("Aggregating tax data..."):
                try:
                    with SessionLocal() as session:
                        aggregator = TaxAggregatorService(session)
                        report = aggregator.generate_report(account_id, tax_year)
                        
                        # Display Metrics
                        st.subheader(f"Report Summary for {account_id} ({tax_year})")
                        m1, m2, m3 = st.columns(3)
                        m1.metric("KAP Line 7 (Kapitalerträge)", f"{report.kap_line_7_kapitalertraege:,.2f} €")
                        m2.metric("KAP Line 8 (Gewinne Aktien)", f"{report.kap_line_8_gewinne_aktien:,.2f} €")
                        m3.metric("KAP Line 9 (Verluste Aktien)", f"{report.kap_line_9_verluste_aktien:,.2f} €")
                        
                        m4, m5, m6 = st.columns(3)
                        m4.metric("KAP Line 10 (Termingeschäfte)", f"{report.kap_line_10_termingeschaefte:,.2f} €")
                        m5.metric("KAP Line 15 (Quellensteuer)", f"{report.kap_line_15_quellensteuer:,.2f} €")
                        m6.metric("Total Realized PnL", f"{report.total_realized_pnl:,.2f} €")
                        
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
