from decimal import Decimal
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from sqlalchemy.orm import Session
from sqlalchemy import select
from ibkr_tax.schemas.report import TaxReport
from ibkr_tax.models.database import Gain, Trade

class ExcelExportService:
    def __init__(self, session: Session):
        self.session = session

    def export(self, report: TaxReport, output_path: str) -> None:
        """
        Produces an elegantly formatted Excel report for German tax consultants.
        """
        wb = Workbook()
        
        # --- Sheet 1: Anlage KAP Summary ---
        summary_sheet = wb.active
        summary_sheet.title = "Anlage KAP Summary"
        
        # Formatting constants
        bold_font = Font(bold=True)
        title_font = Font(bold=True, size=14)
        header_fill = PatternFill(start_color="DDDDDD", end_color="DDDDDD", fill_type="solid")
        euro_format = '#,##0.00 €'
        
        # Row 1: Title
        summary_sheet.merge_cells("A1:C1")
        title_cell = summary_sheet["A1"]
        title_cell.value = "IBKR2KAP — Anlage KAP Bericht"
        title_cell.font = title_font
        title_cell.alignment = Alignment(horizontal="center")
        
        # Row 2: Header Info
        summary_sheet["A2"] = f"Konto: {report.account_id}"
        summary_sheet["B2"] = f"Steuerjahr: {report.tax_year}"
        
        # Rows 4-9: KAP Table
        headers = ["Zeile", "Bezeichnung", "Betrag (EUR)"]
        for col_idx, header in enumerate(headers, 1):
            cell = summary_sheet.cell(row=4, column=col_idx)
            cell.value = header
            cell.font = bold_font
            cell.fill = header_fill
            
        kap_rows = [
            ("7", "Kapitalerträge (Dividenden / Sonstige)", report.kap_line_7_kapitalertraege),
            ("8", "Gewinne aus Aktienveräußerungen", report.kap_line_8_gewinne_aktien),
            ("9", "Verluste aus Aktienveräußerungen", report.kap_line_9_verluste_aktien),
            ("10", "Termingeschäfte (netto)", report.kap_line_10_termingeschaefte),
            ("15", "Anrechenbare ausländische Steuern", report.kap_line_15_quellensteuer),
            ("", "Gesamt realisierter Gewinn/Verlust", report.total_realized_pnl)
        ]
        
        for r_idx, (zeile, desc, val) in enumerate(kap_rows, 5):
            summary_sheet.cell(row=r_idx, column=1).value = zeile
            summary_sheet.cell(row=r_idx, column=2).value = desc
            val_cell = summary_sheet.cell(row=r_idx, column=3)
            val_cell.value = val
            val_cell.number_format = euro_format
            
        # Column widths
        summary_sheet.column_dimensions["A"].width = 8
        summary_sheet.column_dimensions["B"].width = 42
        summary_sheet.column_dimensions["C"].width = 18

        # --- Sheet 2: Gains Detail ---
        detail_sheet = wb.create_sheet("Gains Detail")
        
        detail_headers = [
            "Datum", "Symbol", "Tax Pool", "Quantity", 
            "Proceeds (EUR)", "Cost Basis (EUR)", "Gain/Loss (EUR)"
        ]
        for col_idx, header in enumerate(detail_headers, 1):
            cell = detail_sheet.cell(row=1, column=col_idx)
            cell.value = header
            cell.font = bold_font
            cell.fill = header_fill
            
        # Fetch Gains detail
        # Note: join Gain -> Trade -> Account (matching report.account_id)
        # But we only need Gains where tax_year matches.
        # Joining on Trade to get symbol and settle_date.
        from ibkr_tax.models.database import Account
        stmt = (
            select(Gain)
            .join(Trade, Gain.sell_trade_id == Trade.id)
            .join(Account, Trade.account_id == Account.id)
            .where(Account.account_id == report.account_id)
            .where(Gain.tax_year == report.tax_year)
            .order_by(Trade.settle_date.asc())
        )
        gains = self.session.execute(stmt).scalars().all()
        
        qty_format = '#,##0.0000'
        for r_idx, g in enumerate(gains, 2):
            detail_sheet.cell(row=r_idx, column=1).value = g.sell_trade.settle_date
            detail_sheet.cell(row=r_idx, column=2).value = g.sell_trade.symbol
            detail_sheet.cell(row=r_idx, column=3).value = g.tax_pool
            
            qty_cell = detail_sheet.cell(row=r_idx, column=4)
            qty_cell.value = g.quantity_matched
            qty_cell.number_format = qty_format
            
            p_cell = detail_sheet.cell(row=r_idx, column=5)
            p_cell.value = g.proceeds
            p_cell.number_format = euro_format
            
            c_cell = detail_sheet.cell(row=r_idx, column=6)
            c_cell.value = g.cost_basis_matched
            c_cell.number_format = euro_format
            
            gn_cell = detail_sheet.cell(row=r_idx, column=7)
            gn_cell.value = g.realized_pnl
            gn_cell.number_format = euro_format
            
        detail_sheet.freeze_panes = "A2"
        # Auto-width for detail sheet columns (rough estimate)
        for col in ["A", "B", "C", "D", "E", "F", "G"]:
            detail_sheet.column_dimensions[col].width = 15

        wb.save(output_path)
