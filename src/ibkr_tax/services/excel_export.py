from decimal import Decimal
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload
from ibkr_tax.schemas.report import TaxReport, CombinedTaxReport
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



    def _init_formatting(self):
        """Initializes Excel formatting constants."""
        self.bold_font = Font(bold=True)
        self.title_font = Font(bold=True, size=14)
        self.header_fill = PatternFill(start_color="DDDDDD", end_color="DDDDDD", fill_type="solid")
        self.euro_format = '#,##0.00 €'
        self.qty_format = '#,##0.0000'
        self.date_format = 'yyyy-mm-dd'

    def export(self, report: TaxReport, output_path: str) -> None:
        """
        Produces an elegantly formatted Excel report with full row-level transparency.
        """
        self._init_formatting()
        wb = Workbook()
        
        # 1-8. Normal Sheets
        self._add_summary_sheet(wb, report)
        self._add_matched_gains_sheet(wb, report, "Aktienveräußerungen (Mat.)", "Aktien")
        self._add_matched_gains_sheet(wb, report, "Termingeschäfte (Mat.)", "Termingeschäfte")
        self._add_cash_details_sheet(wb, report)
        self._add_margin_interest_sheet(wb, report)
        self._add_deposits_withdrawals_sheet(wb, report)
        self._add_fx_gains_sheet(wb, report)
        self._add_audit_trail_sheet(wb, report)

        wb.save(output_path)

    def export_combined(self, combined_report: CombinedTaxReport, output_path: str) -> None:
        """
        Produces a combined Excel report for multiple accounts.
        """
        self._init_formatting()
        wb = Workbook()

        # 1. Summary Sheet (Combined + Individual)
        self._add_summary_sheet(wb, combined_report)

        # 2-8. Detail Sheets with "Konto" column enabled
        self._add_matched_gains_sheet(wb, combined_report, "Aktienveräußerungen (Mat.)", "Aktien", show_account=True)
        self._add_matched_gains_sheet(wb, combined_report, "Termingeschäfte (Mat.)", "Termingeschäfte", show_account=True)
        self._add_cash_details_sheet(wb, combined_report, show_account=True)
        self._add_margin_interest_sheet(wb, combined_report, show_account=True)
        self._add_deposits_withdrawals_sheet(wb, combined_report, show_account=True)
        self._add_fx_gains_sheet(wb, combined_report, show_account=True)
        self._add_audit_trail_sheet(wb, combined_report, show_account=True)

        wb.save(output_path)

    def _add_summary_sheet(self, wb, report):
        ws = wb.active
        ws.title = "Anlage KAP Summary"
        
        is_combined = isinstance(report, CombinedTaxReport)
        
        ws.merge_cells("A1:C1")
        title_cell = ws["A1"]
        title_cell.value = "IBKR2KAP — Anlage KAP Bericht" + (" (Kombiniert)" if is_combined else "")
        title_cell.font = self.title_font
        title_cell.alignment = Alignment(horizontal="center")
        
        if is_combined:
            ws["A2"] = f"Konten: {', '.join(report.account_ids)}"
        else:
            ws["A2"] = f"Konto: {report.account_id}"
        ws["B2"] = f"Steuerjahr: {report.tax_year}"
        
        headers = ["Zeile", "Bezeichnung", "Betrag (EUR)"]
        for col_idx, header in enumerate(headers, 1):
            cell = ws.cell(row=4, column=col_idx)
            cell.value = header
            cell.font = self.bold_font
            cell.fill = self.header_fill
            
        def _write_kap_rows(start_row, r_data):
            curr_row = start_row
            for zeile, desc, val in r_data:
                ws.cell(row=curr_row, column=1).value = zeile
                ws.cell(row=curr_row, column=2).value = desc
                val_cell = ws.cell(row=curr_row, column=3)
                val_cell.value = val
                if isinstance(val, (Decimal, float)):
                    val_cell.number_format = self.euro_format
                curr_row += 1
            return curr_row

        def _get_report_rows(rep):
            return [
                ("7", "Kapitalerträge (Dividenden / Zinsen / Ausgleichszahlungen / Sonstige)", rep.kap_line_7_kapitalertraege),
                ("8", "Aktien-Veräußerungsgewinne", rep.kap_line_8_gewinne_aktien),
                ("9", "Aktien-Veräußerungsverluste", rep.kap_line_9_verluste_aktien),
                ("10", "Termingeschäfte (netto)", rep.kap_line_10_termingeschaefte),
                ("", "  - davon Gewinne", rep.kap_termingeschaefte_gains),
                ("", "  - davon Verluste", rep.kap_termingeschaefte_losses),
                ("15", "Anrechenbare ausländische Steuern", rep.kap_line_15_quellensteuer),
                ("", "", ""),
                ("SO", "Fremdwährungsgeschäfte (§ 23 EStG)", ""),
                ("", "  - Gesamtgewinn/-verlust", rep.so_fx_gains_total),
                ("", "  - Davon steuerpflichtig (< 1 Jahr)", rep.so_fx_gains_taxable_1y),
                ("", "  - Davon steuerfrei (> 1 Jahr)", rep.so_fx_gains_tax_free),
                ("", "  - Freigrenze (1000€) unterschritten?", "JA" if rep.so_fx_freigrenze_applies else "NEIN"),
                ("", "", ""),
                ("", "Zusammenfassung nach Verlusttöpfen (§ 20 Abs. 6 EStG)", ""),
                ("", "Aktientopf (Netto: Zeile 8 - 9)", rep.aktien_net_result),
                ("", "  Hinweis: Nur mit Aktiengewinnen verrechenbar.", ""),
                ("", "Allgemeiner Topf (Zeile 7 + 10)", rep.allgemeiner_topf_result),
                ("", "  - davon Dividenden & Zinsen", rep.dividends_interest_total),
                ("", "  - davon Sonstige Kursgewinne (ETFs, etc.)", rep.sonstige_gains_total),
                ("", "  - davon Termingeschäfte (Gains)", rep.kap_termingeschaefte_gains),
                ("", "  - davon Termingeschäfte (Losses)", rep.kap_termingeschaefte_losses),
                ("", "  - davon Termingeschäfte (Netto)", rep.kap_line_10_termingeschaefte),
                ("", "", ""),
                ("", "Marginkosten (Info, nicht abzugsfähig)", rep.margin_interest_paid),
            ]

        # 1. Main Summary (Combined or Single)
        next_r = _write_kap_rows(5, _get_report_rows(report))

        # 2. Individual Summaries (if combined)
        if is_combined:
            for acc_rep in report.per_account_reports:
                next_r += 1
                ws.cell(row=next_r, column=2).value = f"BREAKDOWN: Konto {acc_rep.account_id}"
                ws.cell(row=next_r, column=2).font = self.bold_font
                next_r += 1
                next_r = _write_kap_rows(next_r, _get_report_rows(acc_rep))
            
        ws.column_dimensions["A"].width = 8
        ws.column_dimensions["B"].width = 60
        ws.column_dimensions["C"].width = 20

    def _add_matched_gains_sheet(self, wb, report, title, pool_filter, show_account=False):
        ws = wb.create_sheet(title)
        headers = [
            "Verkaufsdatum", "Anschaffungsdatum", "Symbol", "Quantity", 
            "Erlös (Brutto EUR)", "Kosten (Brutto EUR)", "Spesen (EUR)", "Gewinn/Verlust (EUR)"
        ]
        if show_account:
            headers = ["Konto"] + headers

        for col_idx, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_idx)
            cell.value = header
            cell.font = self.bold_font
            cell.fill = self.header_fill
            

        account_ids = report.account_ids if isinstance(report, CombinedTaxReport) else [report.account_id]

        stmt = (
            select(Gain)
            .options(joinedload(Gain.buy_lot))
            .join(Trade, Gain.sell_trade_id == Trade.id)
            .join(Account, Trade.account_id == Account.id)
            .where(Account.account_id.in_(account_ids))
            .where(Gain.tax_year == report.tax_year)
            .where(Gain.tax_pool == pool_filter)
            .order_by(Account.account_id.asc(), Trade.settle_date.asc())
        )
        gains = self.session.execute(stmt).scalars().all()
        
        for r_idx, g in enumerate(gains, 2):
            col_off = 0
            if show_account:
                ws.cell(row=r_idx, column=1).value = g.sell_trade.account.account_id
                col_off = 1

            ws.cell(row=r_idx, column=1+col_off).value = g.sell_trade.settle_date
            ws.cell(row=r_idx, column=2+col_off).value = g.buy_lot.settle_date
            ws.cell(row=r_idx, column=3+col_off).value = g.sell_trade.symbol
            
            qty_cell = ws.cell(row=r_idx, column=4+col_off)
            qty_cell.value = g.quantity_matched
            qty_cell.number_format = self.qty_format
            
            p_cell = ws.cell(row=r_idx, column=5+col_off)
            p_cell.value = g.proceeds + g.sell_comm
            p_cell.number_format = self.euro_format
            
            c_cell = ws.cell(row=r_idx, column=6+col_off)
            c_cell.value = g.cost_basis_matched - g.buy_comm
            c_cell.number_format = self.euro_format
            
            s_cell = ws.cell(row=r_idx, column=7+col_off)
            s_cell.value = g.buy_comm + g.sell_comm
            s_cell.number_format = self.euro_format

            gn_cell = ws.cell(row=r_idx, column=8+col_off)
            gn_cell.value = g.realized_pnl
            gn_cell.number_format = self.euro_format
            
        ws.freeze_panes = "A2"
        # Adjusted width for account column
        if show_account:
            ws.column_dimensions["A"].width = 15
        
        for col_l in ["A", "B", "C", "D", "E", "F", "G", "H"]:
            real_col = chr(ord(col_l) + (1 if show_account else 0))
            if real_col <= 'I': # safety
                ws.column_dimensions[real_col].width = 15


    def _add_cash_details_sheet(self, wb, report, show_account=False):
        ws = wb.create_sheet("Dividenden, Zinsen & Sonstiges")
        headers = [
            "Zahlungsdatum", "Symbol", "Beschreibung", "Typ", "Währung", 
            "Betrag (Brutto)", "FX Rate", "Betrag (EUR)", "Quellensteuer (EUR)"
        ]
        if show_account:
            headers = ["Konto"] + headers

        for col_idx, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_idx)
            cell.value = header
            cell.font = self.bold_font
            cell.fill = self.header_fill
            

        # Margin/Non-taxable types to exclude from this sheet
        exclude_types = {"broker interest paid", "bond interest paid", "deposits & withdrawals"}
        account_ids = report.account_ids if isinstance(report, CombinedTaxReport) else [report.account_id]

        stmt = (
            select(CashTransaction)
            .join(Account, CashTransaction.account_id == Account.id)
            .where(Account.account_id.in_(account_ids))
            .where(CashTransaction.settle_date.like(f"{report.tax_year}%"))
            .order_by(Account.account_id.asc(), CashTransaction.settle_date.asc())
        )
        all_txs = self.session.execute(stmt).scalars().all()
        # Filter: exclude margin costs and non-taxable cash movements
        txs = [
            ct for ct in all_txs
            if ct.type.lower() not in exclude_types
            and not (ct.type.lower() == "broker interest paid/received" and ct.amount < 0)
        ]
        
        for r_idx, ct in enumerate(txs, 2):
            col_off = 0
            if show_account:
                ws.cell(row=r_idx, column=1).value = ct.account.account_id
                col_off = 1

            ws.cell(row=r_idx, column=1+col_off).value = ct.settle_date
            ws.cell(row=r_idx, column=2+col_off).value = ct.symbol or "--"
            ws.cell(row=r_idx, column=3+col_off).value = ct.description
            ws.cell(row=r_idx, column=4+col_off).value = ct.type
            ws.cell(row=r_idx, column=5+col_off).value = ct.currency
            
            amt_cell = ws.cell(row=r_idx, column=6+col_off)
            amt_cell.value = abs(ct.amount) if ct.type == "Withholding Tax" else ct.amount
            amt_cell.number_format = self.qty_format
            
            ws.cell(row=r_idx, column=7+col_off).value = ct.fx_rate_to_base
            
            eur_cell = ws.cell(row=r_idx, column=8+col_off)
            eur_amt = ct.amount * ct.fx_rate_to_base
            # If it's a dividend/interest, put it in col 8. If tax, put in col 9.
            if ct.type == "Withholding Tax":
                eur_cell.value = 0
                wht_cell = ws.cell(row=r_idx, column=9+col_off)
                wht_cell.value = abs(eur_amt)
                wht_cell.number_format = self.euro_format
            else:
                eur_cell.value = eur_amt
                eur_cell.number_format = self.euro_format
                ws.cell(row=r_idx, column=9+col_off).value = 0
            
        ws.freeze_panes = "A2"
        # Adjust column widths
        desc_col = "D" if show_account else "C"
        ws.column_dimensions[desc_col].width = 40
        
        cols_to_wide = ["A", "B", "D", "E", "F", "G", "H", "I"]
        if show_account:
            cols_to_wide.append("J")

        for col in cols_to_wide:
            if col != desc_col:
                ws.column_dimensions[col].width = 15

    def _add_margin_interest_sheet(self, wb, report, show_account=False):
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
        if show_account:
            detail_headers = ["Konto"] + detail_headers

        for col_idx, header in enumerate(detail_headers, 1):
            cell = ws.cell(row=5, column=col_idx)
            cell.value = header
            cell.font = self.bold_font
            cell.fill = self.header_fill

        # Fetch margin interest transactions
        margin_types = {"broker interest paid", "bond interest paid"}
        account_ids = report.account_ids if isinstance(report, CombinedTaxReport) else [report.account_id]
        
        stmt = (
            select(CashTransaction)
            .join(Account, CashTransaction.account_id == Account.id)
            .where(Account.account_id.in_(account_ids))
            .where(CashTransaction.settle_date.like(f"{report.tax_year}%"))
            .order_by(Account.account_id.asc(), CashTransaction.settle_date.asc())
        )
        all_txs = self.session.execute(stmt).scalars().all()
        margin_txs = [
            ct for ct in all_txs
            if ct.type.lower() in margin_types
            or (ct.type.lower() == "broker interest paid/received" and ct.amount < 0)
        ]

        for r_idx, ct in enumerate(margin_txs, 6):
            col_off = 0
            if show_account:
                ws.cell(row=r_idx, column=1).value = ct.account.account_id
                col_off = 1

            ws.cell(row=r_idx, column=1+col_off).value = ct.settle_date
            ws.cell(row=r_idx, column=2+col_off).value = ct.symbol or "--"
            ws.cell(row=r_idx, column=3+col_off).value = ct.description
            ws.cell(row=r_idx, column=4+col_off).value = ct.currency

            amt_cell = ws.cell(row=r_idx, column=5+col_off)
            amt_cell.value = ct.amount
            amt_cell.number_format = self.qty_format

            ws.cell(row=r_idx, column=6+col_off).value = ct.fx_rate_to_base

            eur_cell = ws.cell(row=r_idx, column=7+col_off)
            eur_cell.value = abs(ct.amount * ct.fx_rate_to_base)
            eur_cell.number_format = self.euro_format

        ws.freeze_panes = "A6"
        desc_col = "D" if show_account else "C"
        ws.column_dimensions[desc_col].width = 40
        for col_l in ["A", "B", "C", "D", "E", "F", "G"]:
            real_col = col_l
            if show_account and col_l != "A":
                 # shift logic for simplicity
                 pass 
            ws.column_dimensions[col_l].width = 15
        if show_account:
             ws.column_dimensions["H"].width = 15

    def _add_deposits_withdrawals_sheet(self, wb, report, show_account=False):
        """Informational sheet for cash deposits and withdrawals."""
        ws = wb.create_sheet("Ein- und Auszahlungen (Info)")
        headers = ["Datum", "Beschreibung", "Währung", "Betrag", "FX Rate", "Betrag (EUR)"]
        if show_account:
            headers = ["Konto"] + headers

        for col_idx, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_idx)
            cell.value = header
            cell.font = self.bold_font
            cell.fill = self.header_fill

        account_ids = report.account_ids if isinstance(report, CombinedTaxReport) else [report.account_id]

        stmt = (
            select(CashTransaction)
            .join(Account, CashTransaction.account_id == Account.id)
            .where(Account.account_id.in_(account_ids))
            .where(CashTransaction.settle_date.like(f"{report.tax_year}%"))
            .order_by(Account.account_id.asc(), CashTransaction.settle_date.asc())
        )
        all_txs = self.session.execute(stmt).scalars().all()
        dw_txs = [ct for ct in all_txs if ct.type.lower() == "deposits & withdrawals"]

        for r_idx, ct in enumerate(dw_txs, 2):
            col_off = 0
            if show_account:
                ws.cell(row=r_idx, column=1).value = ct.account.account_id
                col_off = 1

            ws.cell(row=r_idx, column=1+col_off).value = ct.settle_date
            ws.cell(row=r_idx, column=2+col_off).value = ct.description
            ws.cell(row=r_idx, column=3+col_off).value = ct.currency
            
            amt_cell = ws.cell(row=r_idx, column=4+col_off)
            amt_cell.value = ct.amount
            amt_cell.number_format = self.qty_format
            
            ws.cell(row=r_idx, column=5+col_off).value = ct.fx_rate_to_base
            
            eur_cell = ws.cell(row=r_idx, column=6+col_off)
            eur_cell.value = ct.amount * ct.fx_rate_to_base
            eur_cell.number_format = self.euro_format

        desc_col = "C" if show_account else "B"
        ws.column_dimensions[desc_col].width = 50
        for col_idx in range(1, 8 if show_account else 7):
            col_letter = chr(64 + col_idx)
            if col_letter != desc_col:
                ws.column_dimensions[col_letter].width = 15

    def _add_fx_gains_sheet(self, wb, report, show_account=False):
        ws = wb.create_sheet("Währungsgewinne (§ 23 EStG)")
        fx_headers = [
            "Datum Dispo", "Währung", "Ansch. Datum", "Haltedauer (Tage)", "Betrag",
            "Erlös (EUR)", "Kosten (EUR)", "Gewinn/Verlust (EUR)", "Steuerrelevant?"
        ]
        if show_account:
            fx_headers = ["Konto"] + fx_headers

        for col_idx, header in enumerate(fx_headers, 1):
            cell = ws.cell(row=1, column=col_idx)
            cell.value = header
            cell.font = self.bold_font
            cell.fill = self.header_fill
            

        account_ids = report.account_ids if isinstance(report, CombinedTaxReport) else [report.account_id]

        stmt_fx = (
            select(FXGain)
            .join(Account, FXGain.account_id == Account.id)
            .where(Account.account_id.in_(account_ids))
            .where(FXGain.disposal_date.like(f"{report.tax_year}%"))
            .order_by(Account.account_id.asc(), FXGain.disposal_date.asc())
        )
        fx_gains = self.session.execute(stmt_fx).scalars().all()
        
        for r_idx, g in enumerate(fx_gains, 2):
            col_off = 0
            if show_account:
                ws.cell(row=r_idx, column=1).value = g.account.account_id
                col_off = 1

            ws.cell(row=r_idx, column=1+col_off).value = g.disposal_date
            ws.cell(row=r_idx, column=2+col_off).value = g.fx_lot.currency
            ws.cell(row=r_idx, column=3+col_off).value = g.fx_lot.acquisition_date
            ws.cell(row=r_idx, column=4+col_off).value = g.days_held
            
            amt_cell = ws.cell(row=r_idx, column=5+col_off)
            amt_cell.value = g.amount_matched
            amt_cell.number_format = self.qty_format
            
            p_cell = ws.cell(row=r_idx, column=6+col_off)
            p_cell.value = g.disposal_proceeds_eur
            p_cell.number_format = self.euro_format
            
            c_cell = ws.cell(row=r_idx, column=7+col_off)
            c_cell.value = g.cost_basis_matched_eur
            c_cell.number_format = self.euro_format
            
            gn_cell = ws.cell(row=r_idx, column=8+col_off)
            gn_cell.value = g.realized_pnl_eur
            gn_cell.number_format = self.euro_format
            
            ws.cell(row=r_idx, column=9+col_off).value = "JA" if g.is_taxable_section_23 else "NEIN"
            
        ws.freeze_panes = "A2"
        max_col_idx = 10 if show_account else 9
        for col_idx in range(1, max_col_idx + 1):
            ws.column_dimensions[chr(64 + col_idx)].width = 15

    def _add_audit_trail_sheet(self, wb, report, show_account=False):
        ws = wb.create_sheet("Transaktionsliste (Alle)")
        headers = [
            "Trade ID", "Settle Date", "Symbol", "Cat", "Buy/Sell", "Open/Close",
            "Quantity", "Price", "Currency", "Proceeds (EUR)", "Comm (EUR)", "Taxes (EUR)"
        ]
        if show_account:
            headers = ["Konto"] + headers

        for col_idx, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_idx)
            cell.value = header
            cell.font = self.bold_font
            cell.fill = self.header_fill
            

        account_ids = report.account_ids if isinstance(report, CombinedTaxReport) else [report.account_id]

        stmt = (
            select(Trade)
            .join(Account, Trade.account_id == Account.id)
            .where(Account.account_id.in_(account_ids))
            .where(Trade.settle_date.like(f"{report.tax_year}%"))
            .order_by(Account.account_id.asc(), Trade.settle_date.asc())
        )
        trades = self.session.execute(stmt).scalars().all()
        
        for r_idx, t in enumerate(trades, 2):
            col_off = 0
            if show_account:
                ws.cell(row=r_idx, column=1).value = t.account.account_id
                col_off = 1

            ws.cell(row=r_idx, column=1+col_off).value = t.ib_trade_id
            ws.cell(row=r_idx, column=2+col_off).value = t.settle_date
            ws.cell(row=r_idx, column=3+col_off).value = t.symbol
            ws.cell(row=r_idx, column=4+col_off).value = t.asset_category
            ws.cell(row=r_idx, column=5+col_off).value = t.buy_sell
            ws.cell(row=r_idx, column=6+col_off).value = t.open_close_indicator
            
            qty_cell = ws.cell(row=r_idx, column=7+col_off)
            qty_cell.value = t.quantity
            qty_cell.number_format = self.qty_format
            
            ws.cell(row=r_idx, column=8+col_off).value = t.trade_price
            ws.cell(row=r_idx, column=9+col_off).value = t.currency
            
            p_cell = ws.cell(row=r_idx, column=10+col_off)
            p_cell.value = t.proceeds * t.fx_rate_to_base
            p_cell.number_format = self.euro_format
            
            cm_cell = ws.cell(row=r_idx, column=11+col_off)
            cm_cell.value = t.ib_commission * t.fx_rate_to_base
            cm_cell.number_format = self.euro_format
            
            tx_cell = ws.cell(row=r_idx, column=12+col_off)
            tx_cell.value = t.taxes * t.fx_rate_to_base
            tx_cell.number_format = self.euro_format
            
        ws.freeze_panes = "A2"
        max_col_idx = 13 if show_account else 12
        for col_idx in range(1, max_col_idx + 1):
             ws.column_dimensions[chr(64 + col_idx)].width = 15

