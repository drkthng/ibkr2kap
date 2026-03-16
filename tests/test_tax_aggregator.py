import pytest
from decimal import Decimal
from ibkr_tax.models.database import Account, Trade, Gain, CashTransaction
from ibkr_tax.services.tax_aggregator import TaxAggregatorService

def test_generate_report_with_mixed_data(db_session):
    # 1. Setup Data
    acc = Account(account_id="U1234567")
    db_session.add(acc)
    db_session.commit()

    # Create dummy trades to link to gains
    # We need real Trade objects because Gain joins on Trade
    t1 = Trade(ib_trade_id="T1", account_id=acc.id, symbol="AAPL", asset_category="STK", 
              description="Apple Inc.", trade_date="2024-01-01", settle_date="2024-01-03", 
              currency="USD", fx_rate_to_base=Decimal("0.9"), quantity=Decimal("-10"), 
              trade_price=Decimal("150"), proceeds=Decimal("1500"), buy_sell="SELL")
    
    t2 = Trade(ib_trade_id="T2", account_id=acc.id, symbol="SPX Call", asset_category="OPT", 
              description="SPX Call Option", trade_date="2024-02-01", settle_date="2024-02-03", 
              currency="USD", fx_rate_to_base=Decimal("0.9"), quantity=Decimal("-1"), 
              trade_price=Decimal("10"), proceeds=Decimal("1000"), buy_sell="SELL")

    t3 = Trade(ib_trade_id="T3", account_id=acc.id, symbol="VUSA", asset_category="ETF", 
              description="Vanguard S&P 500", trade_date="2024-03-01", settle_date="2024-03-03", 
              currency="EUR", fx_rate_to_base=Decimal("1.0"), quantity=Decimal("-100"), 
              trade_price=Decimal("80"), proceeds=Decimal("8000"), buy_sell="SELL")

    db_session.add_all([t1, t2, t3])
    db_session.commit()

    # 2. Add Gains for 2024
    g1 = Gain(sell_trade_id=t1.id, buy_lot_id=1, quantity_matched=10, tax_year=2024, 
              proceeds=Decimal("1500"), cost_basis_matched=Decimal("1000"), realized_pnl=Decimal("500"), tax_pool="Aktien")
    
    # Loss in Aktien
    g2 = Gain(sell_trade_id=t1.id, buy_lot_id=2, quantity_matched=5, tax_year=2024, 
              proceeds=Decimal("400"), cost_basis_matched=Decimal("600"), realized_pnl=Decimal("-200"), tax_pool="Aktien")

    # Termingeschäft (Option)
    g3 = Gain(sell_trade_id=t2.id, buy_lot_id=3, quantity_matched=1, tax_year=2024, 
              proceeds=Decimal("1000"), cost_basis_matched=Decimal("800"), realized_pnl=Decimal("200"), tax_pool="Termingeschäfte")

    # Sonstige (ETF)
    g4 = Gain(sell_trade_id=t3.id, buy_lot_id=4, quantity_matched=100, tax_year=2024, 
              proceeds=Decimal("8000"), cost_basis_matched=Decimal("7000"), realized_pnl=Decimal("1000"), tax_pool="Sonstige")

    db_session.add_all([g1, g2, g3, g4])

    # 3. Add Cash Transactions for 2024
    c1 = CashTransaction(account_id=acc.id, symbol="MSFT", description="Dividend", 
                         date_time="2024-05-01", settle_date="2024-05-03", amount=Decimal("100.00"), 
                         type="Dividends", currency="USD", fx_rate_to_base=Decimal("0.9"), report_date="2024-05-01")
    
    c2 = CashTransaction(account_id=acc.id, symbol="MSFT", description="WHT", 
                         date_time="2024-05-01", settle_date="2024-05-03", amount=Decimal("-15.00"), 
                         type="Withholding Tax", currency="USD", fx_rate_to_base=Decimal("0.9"), report_date="2024-05-01")

    # Transaction in different year
    c3 = CashTransaction(account_id=acc.id, symbol="AAPL", description="Dividend", 
                         date_time="2023-12-30", settle_date="2023-12-30", amount=Decimal("50.00"), 
                         type="Dividends", currency="USD", fx_rate_to_base=Decimal("0.9"), report_date="2023-12-30")

    db_session.add_all([c1, c2, c3])
    db_session.commit()

    # 4. Run Aggregator
    service = TaxAggregatorService(db_session)
    report = service.generate_report("U1234567", 2024)

    # 5. Assertions
    # Line 7: Dividends (100 * 0.9 = 90) + Sonstige Gains (1000) = 1090
    assert report.kap_line_7_kapitalertraege == Decimal("1090.00")
    
    # Line 8: Positive Aktien Gain = 500
    assert report.kap_line_8_gewinne_aktien == Decimal("500.00")
    
    # Line 9: Negative Aktien Loss (absolute) = 200
    assert report.kap_line_9_verluste_aktien == Decimal("200.00")
    
    # Line 10: Termingeschäft Gain = 200
    assert report.kap_line_10_termingeschaefte == Decimal("200.00")
    
    # Line 15: Withholding Tax (absolute, in EUR) = 15 * 0.9 = 13.5
    assert report.kap_line_15_quellensteuer == Decimal("13.50")
    
    # Total PnL: 500 - 200 + 200 + 1000 = 1500
    assert report.total_realized_pnl == Decimal("1500.00")

def test_generate_report_empty_year(db_session):
    acc = Account(account_id="U9999999")
    db_session.add(acc)
    db_session.commit()

    service = TaxAggregatorService(db_session)
    report = service.generate_report("U9999999", 2024)

    assert report.kap_line_7_kapitalertraege == Decimal("0.00")
    assert report.kap_line_8_gewinne_aktien == Decimal("0.00")
    assert report.total_realized_pnl == Decimal("0.00")

def test_generate_report_with_missing_cost_basis(db_session):
    from ibkr_tax.models.database import FIFOLot
    # 1. Setup Data
    acc = Account(account_id="U1111111")
    db_session.add(acc)
    db_session.commit()

    # Create a trade and a corresponding FIFOLot with negative remaining_quantity
    t1 = Trade(ib_trade_id="T1_MISSING", account_id=acc.id, symbol="TSLA", asset_category="STK", 
              description="Tesla Inc.", trade_date="2024-01-01", settle_date="2024-01-03", 
              currency="USD", fx_rate_to_base=Decimal("0.9"), quantity=Decimal("-10"), 
              trade_price=Decimal("200"), proceeds=Decimal("2000"), buy_sell="SELL")
    db_session.add(t1)
    db_session.commit()

    lot = FIFOLot(trade_id=t1.id, asset_category="STK", symbol="TSLA", 
                  settle_date="2024-01-03", original_quantity=Decimal("-10"), 
                  remaining_quantity=Decimal("-10"), cost_basis_total=Decimal("0"), 
                  cost_basis_per_share=Decimal("0"))
    db_session.add(lot)
    db_session.commit()

    # 2. Run Aggregator
    service = TaxAggregatorService(db_session)
    report = service.generate_report("U1111111", 2024)

    # 3. Assertions
    assert len(report.missing_cost_basis_warnings) == 1
    assert "Missing cost basis for 10 shares of TSLA" in report.missing_cost_basis_warnings[0]
    assert "first sold on 2024-01-03" in report.missing_cost_basis_warnings[0]
