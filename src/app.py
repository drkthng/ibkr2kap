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

st.sidebar.info(TR["sidebar_info"])

# --- Status Center (Persistent) ---
status_container = st.sidebar.container()
status_container.write("### 📢 Status")
if "last_status" not in st.session_state:
    st.session_state["last_status"] = "Ready."
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
        xml_files = st.file_uploader("Upload Flex XML", type=["xml"], accept_multiple_files=True)
        if xml_files:
            if st.button(TR["btn_process_xml"]):
                for xml_file in xml_files:
                    update_status(TR["status_parsing"].format(xml_file.name))
                    with st.spinner(f"Parsing {xml_file.name}..."):
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".xml") as tmp:
                            tmp.write(xml_file.getvalue())
                            tmp_path = tmp.name
                        
                        try:
                            with SessionLocal() as session:
                                results = run_import(tmp_path, session, file_type="xml")
                                session.commit()
                                update_status(TR["status_success"].format(xml_file.name), type="success")
                                st.success(f"Successfully processed {xml_file.name}")
                                st.json(results["counts"])
                                
                                if results.get("warnings"):
                                    st.warning(f"⚠️ **Unsupported Data Entities Found in {xml_file.name}**")
                                    for warning in results["warnings"]:
                                        st.write(f"- **{warning['entity']}** (Account: {warning['account_id']}): {warning['message']}")
                        except Exception as e:
                            st.error(f"Error processing {xml_file.name}: {e}")
                        finally:
                            if os.path.exists(tmp_path):
                                os.remove(tmp_path)

    with col2:
        csv_files = st.file_uploader("Upload Activity CSV (Fallback)", type=["csv"], accept_multiple_files=True)
        if csv_files:
            if st.button(TR["btn_process_csv"]):
                for csv_file in csv_files:
                    update_status(TR["status_parsing"].format(csv_file.name))
                    with st.spinner(f"Parsing {csv_file.name}..."):
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
                            tmp.write(csv_file.getvalue())
                            tmp_path = tmp.name
                        
                        try:
                            with SessionLocal() as session:
                                results = run_import(tmp_path, session, file_type="csv")
                                session.commit()
                                update_status(TR["status_success"].format(csv_file.name), type="success")
                                st.success(f"Successfully processed {csv_file.name}")
                                st.json(results["counts"])
                                
                                if results.get("warnings"):
                                    st.warning(f"⚠️ **Unsupported Data Entities Found in {csv_file.name}**")
                                    for warning in results["warnings"]:
                                        st.write(f"- **{warning['entity']}** (Account: {warning.get('account_id', 'Unknown')}): {warning['message']}")
                        except Exception as e:
                            st.error(f"Error processing {csv_file.name}: {e}")
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
    st.header(TR["fifo_header"])
    st.markdown("""
    Run the FIFO matching engine to calculate realized gains and losses across all accounts.
    """)
    
    if st.button(TR["btn_run_fifo"]):
        with st.spinner("Executing FIFO logic..."):
            try:
                update_status("Running FIFO Engine...")
                with SessionLocal() as session:
                    runner = FIFORunner(session)
                    runner.run_all()
                    update_status("FIFO Engine Complete", type="success")
                    st.success("FIFO calculation complete for all accounts!")
            except Exception as e:
                st.error(f"Error running FIFO: {e}")

# --- Tab 3: Manual Positions ---
with tabs[2]:
    st.header(TR["manual_header"])
    st.markdown("""
    If you sold positions that were **acquired before your XML data range**, they will appear as
    "Missing Cost Basis" warnings in the Anlage KAP report.

    Use this form to provide the **acquisition date** and **cost basis** for those positions.
    After adding entries, **re-run the FIFO Engine** in the Tax Processing tab.
    """)

    with SessionLocal() as session:
        mp_accounts = get_distinct_account_ids(session)

    if not mp_accounts:
        st.info("No accounts found. Import IBKR data first.")
    else:
        mp_account_id = st.selectbox("Account", options=mp_accounts, key="mp_account_select")

        # Resolve internal DB id
        with SessionLocal() as session:
            from sqlalchemy import select
            mp_acc_db_id = session.execute(
                select(Account.id).where(Account.account_id == mp_account_id)
            ).scalar()

        if mp_acc_db_id is None:
            st.error("Account not found in database.")
        else:
            # --- Show existing manual positions ---
            with SessionLocal() as session:
                positions = get_manual_positions(session, mp_acc_db_id)

            if positions:
                st.subheader(f"Existing Manual Positions ({len(positions)})")
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
                with st.expander("🗑️ Delete a Manual Position"):
                    del_id = st.selectbox(
                        "Select position to delete",
                        options=[p.id for p in positions],
                        format_func=lambda pid: next(
                            f"{p.symbol} — {p.quantity} @ {p.acquisition_date}" for p in positions if p.id == pid
                        ),
                        key="mp_delete_select",
                    )
                    if st.button("🗑️ Delete Selected Position", key="mp_delete_btn"):
                        with SessionLocal() as session:
                            deleted = delete_manual_position(session, del_id)
                        if deleted:
                            st.success("Position deleted. Re-run the FIFO Engine to update results.")
                            st.rerun()
                        else:
                            st.error("Could not find position to delete.")
            else:
                st.info("No manual positions for this account yet.")

            # --- Add form ---
            st.divider()
            st.subheader("Add New Manual Position")
            with st.form("add_manual_position_form", clear_on_submit=False):
                col_sym, col_cat, col_bs, col_oc = st.columns([2, 1, 1, 1])
                with col_sym:
                    mp_symbol = st.text_input("Symbol (e.g. AAPL)", key="mp_symbol_input")
                with col_cat:
                    mp_asset_cat = st.selectbox("Asset Category", ["STK", "OPT", "FUT", "WAR"], key="mp_asset_cat")
                with col_bs:
                    mp_buy_sell = st.selectbox("Buy/Sell", ["BUY", "SELL"], key="mp_buy_sell")
                with col_oc:
                    mp_open_close = st.selectbox("Open/Close", ["O", "C"], key="mp_open_close")

                col_qty, col_price, col_curr, col_fx = st.columns(4)
                with col_qty:
                    mp_qty = st.number_input("Quantity", min_value=0.0001, step=1.0, format="%.4f", key="mp_qty_input")
                with col_price:
                    mp_price = st.number_input("Trade Price", min_value=0.0, step=0.01, format="%.4f", key="mp_price")
                with col_curr:
                    mp_currency = st.text_input("Currency", value="USD", key="mp_currency")
                with col_fx:
                    mp_fx_rate = st.number_input("FX Rate to EUR", min_value=0.0, value=1.0, step=0.0001, format="%.6f", key="mp_fx_rate")

                col_date, col_settle = st.columns(2)
                with col_date:
                    mp_trade_date = st.date_input("Trade Date", key="mp_trade_date")
                with col_settle:
                    mp_settle_date = st.date_input("Settlement Date", key="mp_date_input")

                col_proceeds, col_comm, col_trcosts = st.columns(3)
                with col_proceeds:
                    mp_proceeds = st.number_input("Proceeds", value=0.0, step=0.01, format="%.4f", key="mp_proceeds")
                with col_comm:
                    mp_comm = st.number_input("IB Commission (Trade)", value=0.0, step=0.01, format="%.4f", key="mp_comm")

                mp_desc = st.text_input("Description (optional)", value="", key="mp_desc")



                submitted = st.form_submit_button("➕ Add Manual Position")
                if submitted:
                    if not mp_symbol.strip():
                        st.error("Symbol is required.")
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
    st.markdown("Generate the final tax report figures for a specific account and year.")
    # Fetch available accounts
    with SessionLocal() as session:
        available_accounts = get_distinct_account_ids(session)
    
    if not available_accounts:
        st.info("No accounts found in the database. Please import some IBKR data first.")
    else:
        col_acc, col_year = st.columns(2)
        with col_acc:
            account_selection = st.multiselect("IBKR Account ID(s)", options=available_accounts, default=available_accounts[:1] if available_accounts else [])
        
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
                st.info("Select at least one account.")
                tax_year = None
            elif not available_years:
                st.warning("No common tax years found for these accounts.")
                tax_year = None
            else:
                tax_year = st.selectbox("Tax Year", options=available_years)
        
        if tax_year and st.button(TR["btn_gen_report"]):
            st.session_state["report_accounts"] = account_selection
            st.session_state["report_year"] = tax_year
            update_status(f"Generating report for {tax_year}...")

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
                            st.error("The following sell trades do not have corresponding buy trades. This will lead to an incorrect taxable gain/loss calculation (treated as 100% gain if not resolved).")
                            for warning in report.missing_cost_basis_warnings:
                                w_col1, w_col2 = st.columns([4, 1])
                                with w_col1:
                                    # Use st.code so the user instantly gets a copy button next to the text
                                    st.code(warning.message, language="markdown")
                                with w_col2:
                                    if st.button("📝 Prefill Manual", key=f"prefill_{warning.trade_id}_{warning.symbol}_{warning.date}", on_click=set_prefill_state, args=(warning.symbol, warning.asset_category, warning.quantity, warning.date)):
                                        st.success(f"Prefilled {warning.symbol}! Go to **📝 Manual Positions** tab.")
                            
                            st.info("💡 You can provide cost basis for these positions in the **📝 Manual Positions** tab, then re-run the FIFO Engine.")
                            
                            if not st.checkbox("Generate report anyway despite missing data"):
                                can_show_report = False
                        
                        if can_show_report:
                            # Display Metrics
                            report_title = f"Combined Report Summary ({tax_year})" if is_combined else f"Report Summary for {account_selection[0]} ({tax_year})"
                            st.subheader(report_title)
                            
                            if is_combined:
                                st.info(f"📊 **Accounts Included**: {', '.join(account_selection)}")
                            m1, m2, m3 = st.columns(3)
                            m1.metric("KAP Line 7 (Dividenden / Zinsen / Ausgleichszahlungen / Sonstige)", f"{report.kap_line_7_kapitalertraege:,.2f} €", help=KAP_TOOLTIPS["kap_line_7"])
                            m2.metric("KAP Line 8 (Aktien-Veräußerungsgewinne)", f"{report.kap_line_8_gewinne_aktien:,.2f} €", help=KAP_TOOLTIPS["kap_line_8"])
                            m3.metric("KAP Line 9 (Aktien-Veräußerungsverluste)", f"{report.kap_line_9_verluste_aktien:,.2f} €", help=KAP_TOOLTIPS["kap_line_9"])
                            
                            m4, m5, m6 = st.columns(3)
                            m4.metric("KAP Line 10 (Termingeschäfte Netto)", f"{report.kap_line_10_termingeschaefte:,.2f} €", help=KAP_TOOLTIPS["kap_line_10"])
                            m5.metric("  - davon Gewinne", f"{report.kap_termingeschaefte_gains:,.2f} €")
                            m6.metric("  - davon Verluste", f"{report.kap_termingeschaefte_losses:,.2f} €")
                            
                            st.metric("KAP Line 15 (Quellensteuer)", f"{report.kap_line_15_quellensteuer:,.2f} €", help=KAP_TOOLTIPS["kap_line_15"])
                            
                            st.divider()
                            st.subheader("Zusammenfassung nach Verlusttöpfen")
                            z1, z2, z3 = st.columns(3)
                            z1.metric("Aktientopf (Netto)", f"{report.aktien_net_result:,.2f} €", help=KAP_TOOLTIPS["aktien_net_result"])
                            z2.metric("Allgemeiner Topf result", f"{report.allgemeiner_topf_result:,.2f} €", help=KAP_TOOLTIPS["allgemeiner_topf_result"])
                            # Exploded view for Termingeschäfte in pool summary if desired, 
                            # but we already show it above. Keeping it simple here.
                            z3.metric("Anlage SO (FX Gesamt)", f"{report.so_fx_gains_total:,.2f} €", help="Summe aller Währungsgewinne (Anlage SO).")
                            
                            st.subheader("Anlage SO (§ 23 EStG Fremdwährungsgeschäfte)")
                            s1, s2, s3 = st.columns(3)
                            s1.metric("SO FX Gesamtgewinn", f"{report.so_fx_gains_total:,.2f} €")
                            s2.metric("SO FX Steuerpflichtig (< 1 J.)", f"{report.so_fx_gains_taxable_1y:,.2f} €")
                            s3.metric("SO FX Steuerfrei (> 1 J.)", f"{report.so_fx_gains_tax_free:,.2f} €")

                            if report.so_fx_freigrenze_applies:
                                st.info("ℹ️ **Freigrenze angewendet**: Da die privaten Veräußerungsgewinne (§ 23) unter 1.000 € liegen, bleiben diese steuerfrei.")
                            elif report.so_fx_gains_taxable_1y >= 1000:
                                st.warning("⚠️ **Freigrenze überschritten**: Gewinne ab 1.000 € sind voll steuerpflichtig.")

                            # Margin Interest (informational)
                            if report.margin_interest_paid > 0:
                                st.subheader("💰 Marginkosten (Info)")
                                st.metric(
                                    "Margin-Zinsen (Broker Interest Paid)",
                                    f"{report.margin_interest_paid:,.2f} €",
                                    help="Nicht in Anlage KAP enthalten — Marginzinsen sind gemäß § 20 Abs. 9 EStG nicht als Werbungskosten abzugsfähig."
                                )
                                st.warning(
                                    "⚠️ **Nicht abzugsfähig**: Margin-Zinsen (Broker Interest Paid) stellen "
                                    "Werbungskosten dar, die gemäß § 20 Abs. 9 EStG nicht von Kapitalerträgen "
                                    "abgezogen werden dürfen. Dieser Betrag ist rein informativ und fließt "
                                    "**nicht** in die Berechnung der Anlage KAP ein. Details im Excel-Export "
                                    "auf dem Blatt **Marginkosten (Info)**."
                                )

                            if is_combined:
                                st.divider()
                                st.subheader("Individual Account Breakdowns")
                                for acc_rep in report.per_account_reports:
                                    with st.expander(f"📊 Details for {acc_rep.account_id}"):
                                        am1, am2, am3 = st.columns(3)
                                        am1.metric("KAP 7", f"{acc_rep.kap_line_7_kapitalertraege:,.2f} €")
                                        am2.metric("KAP 8", f"{acc_rep.kap_line_8_gewinne_aktien:,.2f} €")
                                        am3.metric("KAP 9", f"{acc_rep.kap_line_9_verluste_aktien:,.2f} €")
                                        
                                        am4, am5, am6 = st.columns(3)
                                        am4.metric("KAP 10 Netto", f"{acc_rep.kap_line_10_termingeschaefte:,.2f} €")
                                        am5.metric("KAP 10 Gewinne", f"{acc_rep.kap_termingeschaefte_gains:,.2f} €")
                                        am6.metric("KAP 10 Verluste", f"{acc_rep.kap_termingeschaefte_losses:,.2f} €")
                                        st.metric("SO FX", f"{acc_rep.so_fx_gains_total:,.2f} €")

                            with st.expander("ℹ️ Was bedeuten diese Zeilen?"):
                                st.markdown(
                                    "| Zeile | Bezeichnung | Erklärung |\n"
                                    "|---|---|---|\n"
                                    "| **7** | Kapitalerträge | Dividenden, Zinsen, Ausgleichszahlungen und sonstige Gewinne (ETFs, Anleihen) |\n"
                                    "| **8** | Gewinne Aktien | Nur positive Gewinne aus Einzelaktien-Verkäufen |\n"
                                    "| **9** | Verluste Aktien | Aktienverluste (Absolutwert) — nur mit Aktiengewinnen verrechenbar |\n"
                                    "| **10** | Termingeschäfte | Netto-Ergebnis aus Optionen und Futures |\n"
                                    "| **15** | Quellensteuer | Anrechenbare ausländische Steuern (z.B. US-Withholding Tax) |\n"
                                    "\n"
                                    "> 📖 Ausführliche Erklärungen finden Sie im Tab **\"Tax Guide\"** und in der Datei `docs/GERMAN_TAX_THEORY.md`."
                                )
                            st.divider()
                            st.subheader("📥 Export to Excel")
                            
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
                                    title="Save Anlage KAP Report"
                                )
                                root.destroy()
                                
                                if save_path:
                                    if is_combined:
                                        exporter.export_combined(report, save_path)
                                    else:
                                        exporter.export(report, save_path)
                                    st.success(f"Report saved successfully to `{save_path}`!")
                                    st.info("You can now open the file in Excel.")
                                else:
                                    st.warning("Save was cancelled.")
                        
                except Exception as e:
                    st.error(f"Error generating report: {e}")

# --- Tab 5: Database Browser ---
with tabs[4]:
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

# --- Tab 6: Tax Guide ---
with tabs[5]:
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
