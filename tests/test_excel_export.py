import os
import pytest
from decimal import Decimal
from openpyxl import load_workbook
from ibkr_tax.models.database import Account, Trade, Gain, CashTransaction
from ibkr_tax.schemas.report import TaxReport
from ibkr_tax.services.excel_export import ExcelExportService

def _build_minimal_db(db_session):
    # 1. Setup Account
    acc = Account(account_id="U1234567")
    db_session.add(acc)
    db_session.commit()

    # 2. Add sample trades
    t1 = Trade(ib_trade_id="T1", account_id=acc.id, symbol="AAPL", asset_category="STK", 
              description="Apple Inc.", trade_date="2024-01-01", settle_date="2024-01-03", 
              currency="USD", fx_rate_to_base=Decimal("0.9"), quantity=Decimal("-10"), 
              trade_price=Decimal("150"), proceeds=Decimal("1500"), buy_sell="SELL")
    
    t2 = Trade(ib_trade_id="T2", account_id=acc.id, symbol="MSFT", asset_category="STK", 
              description="Microsoft", trade_date="2024-06-10", settle_date="2024-06-12", 
              currency="USD", fx_rate_to_base=Decimal("0.9"), quantity=Decimal("-5"), 
              trade_price=Decimal("400"), proceeds=Decimal("2000"), buy_sell="SELL")

    db_session.add_all([t1, t2])
    db_session.commit()

    # 3. Add sample Gains
    g1 = Gain(sell_trade_id=t1.id, buy_lot_id=1, quantity_matched=10, tax_year=2024, 
              proceeds=Decimal("1500"), cost_basis_matched=Decimal("1000"), 
              realized_pnl=Decimal("500"), tax_pool="Aktien")
    
    g2 = Gain(sell_trade_id=t2.id, buy_lot_id=2, quantity_matched=5, tax_year=2024, 
              proceeds=Decimal("2000"), cost_basis_matched=Decimal("2200"), 
              realized_pnl=Decimal("-200"), tax_pool="Aktien")

    db_session.add_all([g1, g2])
    db_session.commit()

    return acc

def test_export_creates_file(db_session, tmp_path):
    report = TaxReport(account_id="U1234567", tax_year=2024)
    output_file = str(tmp_path / "test_report.xlsx")
    
    service = ExcelExportService(db_session)
    service.export(report, output_file)
    
    assert os.path.exists(output_file)
    
    wb = load_workbook(output_file)
    assert "Anlage KAP Summary" in wb.sheetnames
    assert "Gains Detail" in wb.sheetnames

def test_summary_sheet_values(db_session, tmp_path):
    report = TaxReport(
        account_id="U1234567", 
        tax_year=2024,
        kap_line_7_kapitalertraege=Decimal("100.00"),
        kap_line_8_gewinne_aktien=Decimal("500.00"),
        kap_line_9_verluste_aktien=Decimal("200.00"),
        kap_line_10_termingeschaefte=Decimal("150.00"),
        kap_line_15_quellensteuer=Decimal("15.00"),
        total_realized_pnl=Decimal("600.00")
    )
    output_file = str(tmp_path / "summary_test.xlsx")
    
    service = ExcelExportService(db_session)
    service.export(report, output_file)
    
    wb = load_workbook(output_file)
    ws = wb["Anlage KAP Summary"]
    
    # Map row contents to values
    # Col A is Zeile, Col B is description, Col C is value
    data = {}
    for row in range(5, 11):
        zeile = ws.cell(row=row, column=1).value
        # If zeile is None/empty string, it's the Total line
        key = str(zeile) if zeile else "TOTAL"
        data[key] = ws.cell(row=row, column=3).value
        
    assert Decimal(str(data["7"])) == Decimal("100.00")
    assert Decimal(str(data["8"])) == Decimal("500.00")
    assert Decimal(str(data["9"])) == Decimal("200.00")
    assert Decimal(str(data["10"])) == Decimal("150.00")
    assert Decimal(str(data["15"])) == Decimal("15.00")
    assert Decimal(str(data["TOTAL"])) == Decimal("600.00")

def test_gains_detail_sheet_row_count(db_session, tmp_path):
    # Setup 2 gains in DB
    acc = _build_minimal_db(db_session)
    
    report = TaxReport(account_id=acc.account_id, tax_year=2024)
    output_file = str(tmp_path / "detail_test.xlsx")
    
    service = ExcelExportService(db_session)
    service.export(report, output_file)
    
    wb = load_workbook(output_file)
    ws = wb["Gains Detail"]
    
    # Count rows excluding header
    # max_row works if there's no trailing empty data
    rows = list(ws.iter_rows(min_row=2, values_only=True))
    assert len(rows) == 2
    # Verify some content from the first gain (AAPL)
    assert rows[0][1] == "AAPL" # Symbol
    assert rows[0][2] == "Aktien" # Tax Pool

def test_gains_detail_sorted_by_date(db_session, tmp_path):
    # Setup data with specific dates
    acc = Account(account_id="U888")
    db_session.add(acc)
    db_session.commit()

    # T1 late in the year, T2 early
    t1 = Trade(ib_trade_id="TX1", account_id=acc.id, symbol="Z", asset_category="STK", 
              description="Z", trade_date="2024-12-01", settle_date="2024-12-03", 
              currency="EUR", fx_rate_to_base=Decimal("1"), quantity=Decimal("-1"), 
              trade_price=Decimal("100"), proceeds=Decimal("100"), buy_sell="SELL")
    
    t2 = Trade(ib_trade_id="TX2", account_id=acc.id, symbol="A", asset_category="STK", 
              description="A", trade_date="2024-01-01", settle_date="2024-01-03", 
              currency="EUR", fx_rate_to_base=Decimal("1"), quantity=Decimal("-1"), 
              trade_price=Decimal("100"), proceeds=Decimal("100"), buy_sell="SELL")

    db_session.add_all([t1, t2])
    db_session.commit()

    g1 = Gain(sell_trade_id=t1.id, buy_lot_id=10, quantity_matched=1, tax_year=2024, 
              proceeds=Decimal("100"), cost_basis_matched=Decimal("90"), 
              realized_pnl=Decimal("10"), tax_pool="Aktien")
    
    g2 = Gain(sell_trade_id=t2.id, buy_lot_id=11, quantity_matched=1, tax_year=2024, 
              proceeds=Decimal("100"), cost_basis_matched=Decimal("90"), 
              realized_pnl=Decimal("10"), tax_pool="Aktien")

    db_session.add_all([g1, g2])
    db_session.commit()

    report = TaxReport(account_id="U888", tax_year=2024)
    output_file = str(tmp_path / "sort_test.xlsx")
    
    service = ExcelExportService(db_session)
    service.export(report, output_file)
    
    wb = load_workbook(output_file)
    ws = wb["Gains Detail"]
    
    dates = [ws.cell(row=r, column=1).value for r in range(2, 4)]
    # Should be sorted: 2024-01-03 then 2024-12-03
    assert dates[0] == "2024-01-03"
    assert dates[1] == "2024-12-03"
