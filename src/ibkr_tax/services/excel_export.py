from decimal import Decimal
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload
from ibkr_tax.schemas.report import TaxReport
from ibkr_tax.models.database import Account, Gain, Trade, FXGain, FXFIFOLot, CashTransaction

class ExcelExportService:
    def __init__(self, session: Session):
        self.session = session

        # Formatting placeholders (initialized in export())
        self.bold_font: Font | None = None
        self.title_font: Font | None = None
        self.header_fill: PatternFill | None = None
        self.euro_format: str = ""
        self.qty_format: str = ""
        self.date_format: str = ""



    def export(self, report: TaxReport, output_path: str) -> None:
        """
        Produces an elegantly formatted Excel report with full row-level transparency.
        """
        wb = Workbook()
        
        # Formatting constants
        self.bold_font = Font(bold=True)
        self.title_font = Font(bold=True, size=14)
        self.header_fill = PatternFill(start_color="DDDDDD", end_color="DDDDDD", fill_type="solid")
        self.euro_format = '#,##0.00 €'
        self.qty_format = '#,##0.0000'
        self.date_format = 'yyyy-mm-dd'

        # 1. Summary Sheet
        self._add_summary_sheet(wb, report)
        
        # 2. Detailed Gains (Stock)
        self._add_matched_gains_sheet(wb, report, "Aktienveräußerungen (Mat.)", "Aktien")
        
        # 3. Detailed Gains (Options/Futures)
        self._add_matched_gains_sheet(wb, report, "Termingeschäfte (Mat.)", "Termingeschäfte")
        
        # 4. Dividends & Interest
        self._add_cash_details_sheet(wb, report)
        
        # 5. Margin Interest (informational, non-deductible)
        self._add_margin_interest_sheet(wb, report)
        
        # 6. FX Gains (§ 23)
        self._add_fx_gains_sheet(wb, report)
        
        # 7. Audit Trail: All Trades
        self._add_audit_trail_sheet(wb, report)

        wb.save(output_path)

    def _add_summary_sheet(self, wb, report):
        ws = wb.active
        ws.title = "Anlage KAP Summary"
        
        ws.merge_cells("A1:C1")
        title_cell = ws["A1"]
        title_cell.value = "IBKR2KAP — Anlage KAP Bericht"
        title_cell.font = self.title_font
        title_cell.alignment = Alignment(horizontal="center")
        
        ws["A2"] = f"Konto: {report.account_id}"
        ws["B2"] = f"Steuerjahr: {report.tax_year}"
        
        headers = ["Zeile", "Bezeichnung", "Betrag (EUR)"]
        for col_idx, header in enumerate(headers, 1):
            cell = ws.cell(row=4, column=col_idx)
            cell.value = header
            cell.font = self.bold_font
            cell.fill = self.header_fill
            
        kap_rows = [
            ("7", "Kapitalerträge (Dividenden / Zinsen / Ausgleichszahlungen / Sonstige)", report.kap_line_7_kapitalertraege),
            ("8", "Aktien-Veräußerungsgewinne", report.kap_line_8_gewinne_aktien),
            ("9", "Aktien-Veräußerungsverluste", report.kap_line_9_verluste_aktien),
            ("10", "Termingeschäfte (netto)", report.kap_line_10_termingeschaefte),
            ("15", "Anrechenbare ausländische Steuern", report.kap_line_15_quellensteuer),
            ("", "", ""),
            ("SO", "Fremdwährungsgeschäfte (§ 23 EStG)", ""),
            ("", "  - Gesamtgewinn/-verlust", report.so_fx_gains_total),
            ("", "  - Davon steuerpflichtig (< 1 Jahr)", report.so_fx_gains_taxable_1y),
            ("", "  - Davon steuerfrei (> 1 Jahr)", report.so_fx_gains_tax_free),
            ("", "  - Freigrenze (1000€) unterschritten?", "JA" if report.so_fx_freigrenze_applies else "NEIN"),
            ("", "", ""),
            ("", "Gesamt realisierter Gewinn/Verlust (KAP + SO)", report.total_realized_pnl)
        ]
        
        for r_idx, (zeile, desc, val) in enumerate(kap_rows, 5):
            ws.cell(row=r_idx, column=1).value = zeile
            ws.cell(row=r_idx, column=2).value = desc
            val_cell = ws.cell(row=r_idx, column=3)
            val_cell.value = val
            if isinstance(val, (Decimal, float)):
                val_cell.number_format = self.euro_format
            
        ws.column_dimensions["A"].width = 8
        ws.column_dimensions["B"].width = 60
        ws.column_dimensions["C"].width = 20

    def _add_matched_gains_sheet(self, wb, report, title, pool_filter):
        ws = wb.create_sheet(title)
        headers = [
            "Verkaufsdatum", "Anschaffungsdatum", "Symbol", "Quantity", 
            "Erlös (Brutto EUR)", "Kosten (Brutto EUR)", "Spesen (EUR)", "Gewinn/Verlust (EUR)"
        ]
        for col_idx, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_idx)
            cell.value = header
            cell.font = self.bold_font
            cell.fill = self.header_fill
            

        stmt = (
            select(Gain)
            .options(joinedload(Gain.buy_lot))
            .join(Trade, Gain.sell_trade_id == Trade.id)
            .join(Account, Trade.account_id == Account.id)
            .where(Account.account_id == report.account_id)
            .where(Gain.tax_year == report.tax_year)
            .where(Gain.tax_pool == pool_filter)
            .order_by(Trade.settle_date.asc())
        )
        gains = self.session.execute(stmt).scalars().all()
        
        for r_idx, g in enumerate(gains, 2):
            ws.cell(row=r_idx, column=1).value = g.sell_trade.settle_date
            ws.cell(row=r_idx, column=2).value = g.buy_lot.settle_date
            ws.cell(row=r_idx, column=3).value = g.sell_trade.symbol
            
            qty_cell = ws.cell(row=r_idx, column=4)
            qty_cell.value = g.quantity_matched
            qty_cell.number_format = self.qty_format
            
            p_cell = ws.cell(row=r_idx, column=5)
            # Erlös (Brutto) = Net proceeds + sell_comm
            p_cell.value = g.proceeds + g.sell_comm
            p_cell.number_format = self.euro_format
            
            c_cell = ws.cell(row=r_idx, column=6)
            # Kosten (Brutto) = Cost basis matched - buy_comm
            c_cell.value = g.cost_basis_matched - g.buy_comm
            c_cell.number_format = self.euro_format
            
            s_cell = ws.cell(row=r_idx, column=7)
            # Spesen = buy_comm + sell_comm
            s_cell.value = g.buy_comm + g.sell_comm
            s_cell.number_format = self.euro_format

            gn_cell = ws.cell(row=r_idx, column=8)
            gn_cell.value = g.realized_pnl
            gn_cell.number_format = self.euro_format
            
        ws.freeze_panes = "A2"
        for col in ["A", "B", "C", "D", "E", "F", "G", "H"]:
            ws.column_dimensions[col].width = 15


    def _add_cash_details_sheet(self, wb, report):
        ws = wb.create_sheet("Dividenden, Zinsen & Sonstiges")
        headers = [
            "Zahlungsdatum", "Symbol", "Beschreibung", "Typ", "Währung", 
            "Betrag (Brutto)", "FX Rate", "Betrag (EUR)", "Quellensteuer (EUR)"
        ]
        for col_idx, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_idx)
            cell.value = header
            cell.font = self.bold_font
            cell.fill = self.header_fill
            

        # Margin interest types to exclude from this sheet (shown in separate Marginkosten sheet)
        margin_types = {"Broker Interest Paid"}

        stmt = (
            select(CashTransaction)
            .join(Account, CashTransaction.account_id == Account.id)
            .where(Account.account_id == report.account_id)
            .where(CashTransaction.settle_date.like(f"{report.tax_year}%"))
            .order_by(CashTransaction.settle_date.asc())
        )
        all_txs = self.session.execute(stmt).scalars().all()
        # Filter: exclude explicit 'Broker Interest Paid' and negative 'Broker Interest Paid/Received'
        txs = [
            ct for ct in all_txs
            if ct.type not in margin_types
            and not (ct.type == "Broker Interest Paid/Received" and ct.amount < 0)
        ]
        
        for r_idx, ct in enumerate(txs, 2):
            ws.cell(row=r_idx, column=1).value = ct.settle_date
            ws.cell(row=r_idx, column=2).value = ct.symbol or "--"
            ws.cell(row=r_idx, column=3).value = ct.description
            ws.cell(row=r_idx, column=4).value = ct.type
            ws.cell(row=r_idx, column=5).value = ct.currency
            
            amt_cell = ws.cell(row=r_idx, column=6)
            amt_cell.value = abs(ct.amount) if ct.type == "Withholding Tax" else ct.amount
            amt_cell.number_format = self.qty_format
            
            ws.cell(row=r_idx, column=7).value = ct.fx_rate_to_base
            
            eur_cell = ws.cell(row=r_idx, column=8)
            eur_amt = ct.amount * ct.fx_rate_to_base
            # If it's a dividend/interest, put it in col 8. If tax, put in col 9.
            if ct.type == "Withholding Tax":
                eur_cell.value = 0
                wht_cell = ws.cell(row=r_idx, column=9)
                wht_cell.value = abs(eur_amt)
                wht_cell.number_format = self.euro_format
            else:
                eur_cell.value = eur_amt
                eur_cell.number_format = self.euro_format
                ws.cell(row=r_idx, column=9).value = 0
            
        ws.freeze_panes = "A2"
        ws.column_dimensions["C"].width = 40
        for col in ["A", "B", "D", "E", "F", "G", "H", "I"]:
            ws.column_dimensions[col].width = 15

    def _add_margin_interest_sheet(self, wb, report):
        """Informational sheet for margin interest paid — not deductible per § 20 Abs. 9 EStG."""
        ws = wb.create_sheet("Marginkosten (Info)")

        # Header note
        ws.merge_cells("A1:G1")
        note_cell = ws["A1"]
        note_cell.value = (
            "⚠️ Marginzinsen (Broker Interest Paid) sind gemäß § 20 Abs. 9 EStG "
            "nicht als Werbungskosten abzugsfähig und fließen NICHT in die Anlage KAP ein."
        )
        note_cell.font = Font(bold=True, color="CC0000")
        note_cell.alignment = Alignment(wrap_text=True)
        ws.row_dimensions[1].height = 40

        # Summary row
        ws["A3"] = "Gesamt Marginzinsen (EUR):"
        ws["A3"].font = self.bold_font
        summary_cell = ws["B3"]
        summary_cell.value = report.margin_interest_paid
        summary_cell.number_format = self.euro_format
        summary_cell.font = self.bold_font

        # Detail headers
        detail_headers = [
            "Zahlungsdatum", "Symbol", "Beschreibung", "Währung",
            "Betrag (Brutto)", "FX Rate", "Betrag (EUR)"
        ]
        for col_idx, header in enumerate(detail_headers, 1):
            cell = ws.cell(row=5, column=col_idx)
            cell.value = header
            cell.font = self.bold_font
            cell.fill = self.header_fill

        # Fetch margin interest transactions
        margin_types = {"Broker Interest Paid"}
        stmt = (
            select(CashTransaction)
            .join(Account, CashTransaction.account_id == Account.id)
            .where(Account.account_id == report.account_id)
            .where(CashTransaction.settle_date.like(f"{report.tax_year}%"))
            .order_by(CashTransaction.settle_date.asc())
        )
        all_txs = self.session.execute(stmt).scalars().all()
        margin_txs = [
            ct for ct in all_txs
            if ct.type in margin_types
            or (ct.type == "Broker Interest Paid/Received" and ct.amount < 0)
        ]

        for r_idx, ct in enumerate(margin_txs, 6):
            ws.cell(row=r_idx, column=1).value = ct.settle_date
            ws.cell(row=r_idx, column=2).value = ct.symbol or "--"
            ws.cell(row=r_idx, column=3).value = ct.description
            ws.cell(row=r_idx, column=4).value = ct.currency

            amt_cell = ws.cell(row=r_idx, column=5)
            amt_cell.value = ct.amount
            amt_cell.number_format = self.qty_format

            ws.cell(row=r_idx, column=6).value = ct.fx_rate_to_base

            eur_cell = ws.cell(row=r_idx, column=7)
            eur_cell.value = abs(ct.amount * ct.fx_rate_to_base)
            eur_cell.number_format = self.euro_format

        ws.freeze_panes = "A6"
        ws.column_dimensions["C"].width = 40
        for col in ["A", "B", "D", "E", "F", "G"]:
            ws.column_dimensions[col].width = 15

    def _add_fx_gains_sheet(self, wb, report):
        ws = wb.create_sheet("Währungsgewinne (§ 23 EStG)")
        fx_headers = [
            "Datum Dispo", "Währung", "Ansch. Datum", "Haltedauer (Tage)", "Betrag",
            "Erlös (EUR)", "Kosten (EUR)", "Gewinn/Verlust (EUR)", "Steuerrelevant?"
        ]
        for col_idx, header in enumerate(fx_headers, 1):
            cell = ws.cell(row=1, column=col_idx)
            cell.value = header
            cell.font = self.bold_font
            cell.fill = self.header_fill
            

        stmt_fx = (
            select(FXGain)
            .join(Account, FXGain.account_id == Account.id)
            .where(Account.account_id == report.account_id)
            .where(FXGain.disposal_date.like(f"{report.tax_year}%"))
            .order_by(FXGain.disposal_date.asc())
        )
        fx_gains = self.session.execute(stmt_fx).scalars().all()
        
        for r_idx, g in enumerate(fx_gains, 2):
            ws.cell(row=r_idx, column=1).value = g.disposal_date
            ws.cell(row=r_idx, column=2).value = g.fx_lot.currency
            ws.cell(row=r_idx, column=3).value = g.fx_lot.acquisition_date
            ws.cell(row=r_idx, column=4).value = g.days_held
            
            amt_cell = ws.cell(row=r_idx, column=5)
            amt_cell.value = g.amount_matched
            amt_cell.number_format = self.qty_format
            
            p_cell = ws.cell(row=r_idx, column=6)
            p_cell.value = g.disposal_proceeds_eur
            p_cell.number_format = self.euro_format
            
            c_cell = ws.cell(row=r_idx, column=7)
            c_cell.value = g.cost_basis_matched_eur
            c_cell.number_format = self.euro_format
            
            gn_cell = ws.cell(row=r_idx, column=8)
            gn_cell.value = g.realized_pnl_eur
            gn_cell.number_format = self.euro_format
            
            ws.cell(row=r_idx, column=9).value = "JA" if g.is_taxable_section_23 else "NEIN"
            
        ws.freeze_panes = "A2"
        for col in ["A", "B", "C", "D", "E", "F", "G", "H", "I"]:
            ws.column_dimensions[col].width = 15

    def _add_audit_trail_sheet(self, wb, report):
        ws = wb.create_sheet("Transaktionsliste (Alle)")
        headers = [
            "Trade ID", "Settle Date", "Symbol", "Cat", "Buy/Sell", "Open/Close",
            "Quantity", "Price", "Currency", "Proceeds (EUR)", "Comm (EUR)", "Taxes (EUR)"
        ]
        for col_idx, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_idx)
            cell.value = header
            cell.font = self.bold_font
            cell.fill = self.header_fill
            

        stmt = (
            select(Trade)
            .join(Account, Trade.account_id == Account.id)
            .where(Account.account_id == report.account_id)
            .where(Trade.settle_date.like(f"{report.tax_year}%"))
            .order_by(Trade.settle_date.asc())
        )
        trades = self.session.execute(stmt).scalars().all()
        
        for r_idx, t in enumerate(trades, 2):
            ws.cell(row=r_idx, column=1).value = t.ib_trade_id
            ws.cell(row=r_idx, column=2).value = t.settle_date
            ws.cell(row=r_idx, column=3).value = t.symbol
            ws.cell(row=r_idx, column=4).value = t.asset_category
            ws.cell(row=r_idx, column=5).value = t.buy_sell
            ws.cell(row=r_idx, column=6).value = t.open_close_indicator
            
            qty_cell = ws.cell(row=r_idx, column=7)
            qty_cell.value = t.quantity
            qty_cell.number_format = self.qty_format
            
            ws.cell(row=r_idx, column=8).value = t.trade_price
            ws.cell(row=r_idx, column=9).value = t.currency
            
            p_cell = ws.cell(row=r_idx, column=10)
            p_cell.value = t.proceeds * t.fx_rate_to_base
            p_cell.number_format = self.euro_format
            
            cm_cell = ws.cell(row=r_idx, column=11)
            cm_cell.value = t.ib_commission * t.fx_rate_to_base
            cm_cell.number_format = self.euro_format
            
            tx_cell = ws.cell(row=r_idx, column=12)
            tx_cell.value = t.taxes * t.fx_rate_to_base
            tx_cell.number_format = self.euro_format
            
        ws.freeze_panes = "A2"
        for col in ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L"]:
            ws.column_dimensions[col].width = 15

