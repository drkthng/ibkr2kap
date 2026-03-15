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
    st.info("Execution logic will be implemented in the next wave.")

# --- Tab 3: Anlage KAP Report (Placeholder for Plan 12.2) ---
with tabs[2]:
    st.header("Anlage KAP Generation")
    st.info("Reporting logic will be implemented in the next wave.")
