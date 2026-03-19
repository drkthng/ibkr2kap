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
    
    # Aktientopf Net: 500 (G) - 200 (L) = 300
    assert report.aktien_net_result == Decimal("300.00")

    # Allgemeiner Topf: 1090 (Line 7) + 200 (Line 10) = 1290
    assert report.allgemeiner_topf_result == Decimal("1290.00")

    # Sub-components
    assert report.dividends_interest_total == Decimal("90.00")
    assert report.sonstige_gains_total == Decimal("1000.00")

def test_generate_report_empty_year(db_session):
    acc = Account(account_id="U9999999")
    db_session.add(acc)
    db_session.commit()

    service = TaxAggregatorService(db_session)
    report = service.generate_report("U9999999", 2024)

    assert report.kap_line_7_kapitalertraege == Decimal("0.00")
    assert report.kap_line_8_gewinne_aktien == Decimal("0.00")
    assert report.aktien_net_result == Decimal("0.00")
    assert report.allgemeiner_topf_result == Decimal("0.00")

def test_generate_report_with_missing_cost_basis(db_session):
    from ibkr_tax.models.database import FIFOLot
    # 1. Setup Data
    acc = Account(account_id="U1111111")
    db_session.add(acc)
    db_session.commit()

    # Create a trade and a corresponding FIFOLot with negative remaining_quantity for 2024
    t1 = Trade(ib_trade_id="T1_MISSING", account_id=acc.id, symbol="TSLA", asset_category="STK", 
              description="Tesla Inc.", trade_date="2024-01-01", settle_date="2024-01-03", 
              currency="USD", fx_rate_to_base=Decimal("0.9"), quantity=Decimal("-10"), 
              trade_price=Decimal("200"), proceeds=Decimal("2000"), buy_sell="SELL")
    
    # Create another trade and lot for 2025 to ensure it is filtered out of the 2024 report
    t2 = Trade(ib_trade_id="T2_MISSING", account_id=acc.id, symbol="AAPL", asset_category="STK", 
              description="Apple Inc.", trade_date="2025-01-01", settle_date="2025-01-03", 
              currency="USD", fx_rate_to_base=Decimal("0.9"), quantity=Decimal("-5"), 
              trade_price=Decimal("200"), proceeds=Decimal("1000"), buy_sell="SELL")
    db_session.add_all([t1, t2])
    db_session.commit()

    lot1 = FIFOLot(trade_id=t1.id, asset_category="STK", symbol="TSLA", 
                  settle_date="2024-01-03", original_quantity=Decimal("-10"), 
                  remaining_quantity=Decimal("-10"), cost_basis_total=Decimal("0"), 
                  cost_basis_per_share=Decimal("0"))
    lot2 = FIFOLot(trade_id=t2.id, asset_category="STK", symbol="AAPL", 
                  settle_date="2025-01-03", original_quantity=Decimal("-5"), 
                  remaining_quantity=Decimal("-5"), cost_basis_total=Decimal("0"), 
                  cost_basis_per_share=Decimal("0"))
    db_session.add_all([lot1, lot2])
    db_session.commit()

    # 2. Run Aggregator for 2024
    service = TaxAggregatorService(db_session)
    report = service.generate_report("U1111111", 2024)

    # 3. Assertions
    # Should only return 1 warning for 2024, the 2025 one should be ignored
    assert len(report.missing_cost_basis_warnings) == 1
    warning = report.missing_cost_basis_warnings[0]
    assert "Sold 10 TSLA" in warning.message
    assert "on 2024-01-03" in warning.message
    assert "(ID: T1_MISSING)" in warning.message
    assert warning.symbol == "TSLA"
    assert warning.quantity == Decimal("10")
    assert warning.date == "2024-01-03"

def test_generate_report_filters_eur_symbols(db_session):
    from ibkr_tax.models.database import FIFOLot
    # 1. Setup Data
    acc = Account(account_id="U3333333")
    db_session.add(acc)
    db_session.commit()

    # Create a trade and a FIFOLot for EUR.USD in the symbol engine
    # This simulates "garbage" from previous versions
    t1 = Trade(ib_trade_id="T_EUR_GARBAGE", account_id=acc.id, symbol="EUR.USD", asset_category="CASH", 
              description="EUR.USD", trade_date="2024-01-01", settle_date="2024-01-03", 
              currency="USD", fx_rate_to_base=Decimal("0.9"), quantity=Decimal("-1000"), 
              trade_price=Decimal("1.1"), proceeds=Decimal("1100"), buy_sell="SELL")
    db_session.add(t1)
    db_session.commit()

    lot1 = FIFOLot(trade_id=t1.id, asset_category="CASH", symbol="EUR.USD", 
                  settle_date="2024-01-03", original_quantity=Decimal("-1000"), 
                  remaining_quantity=Decimal("-1000"), cost_basis_total=Decimal("0"), 
                  cost_basis_per_share=Decimal("0"))
    db_session.add(lot1)
    db_session.commit()

    # 2. Run Aggregator
    service = TaxAggregatorService(db_session)
    report = service.generate_report("U3333333", 2024)

    # 3. Assertions: Should be filtered out
    assert len(report.missing_cost_basis_warnings) == 0

def test_generate_report_no_fx_warnings_per_redesign(db_session):
    from ibkr_tax.models.database import FXFIFOLot
    # 1. Setup Data
    acc = Account(account_id="U2222222")
    db_session.add(acc)
    db_session.commit()

    # Create a negative FX lot for 2024 - should NOT trigger a warning in the asset engine
    lot = FXFIFOLot(account_id=acc.id, currency="USD", acquisition_date="2024-06-01",
                    original_amount=Decimal("-100"), remaining_amount=Decimal("-100"),
                    cost_basis_total_eur=Decimal("90"), cost_basis_per_unit_eur=Decimal("0.9"))
    db_session.add(lot)
    db_session.commit()

    # 2. Run Aggregator for 2024
    service = TaxAggregatorService(db_session)
    report = service.generate_report("U2222222", 2024)

    # 3. Assertions: FX warnings are removed per Phase 29 redesign
    assert len(report.missing_cost_basis_warnings) == 0

def test_margin_interest_handling(db_session):
    # 1. Setup Data: Mixture of paid and received interest (CSV and XML styles)
    acc = Account(account_id="U8888888")
    db_session.add(acc)
    db_session.commit()

    # XML style: combined type, distinguished by sign
    c1 = CashTransaction(account_id=acc.id, symbol="--", description="Margin Interest (Paid)", 
                         date_time="2024-06-01", settle_date="2024-06-01", amount=Decimal("-50.00"), 
                         type="Broker Interest Paid/Received", currency="EUR", fx_rate_to_base=Decimal("1.0"),
                         report_date="2024-06-01")
    
    c2 = CashTransaction(account_id=acc.id, symbol="--", description="Broker Interest (Received)", 
                         date_time="2024-06-15", settle_date="2024-06-15", amount=Decimal("10.00"), 
                         type="Broker Interest Paid/Received", currency="EUR", fx_rate_to_base=Decimal("1.0"),
                         report_date="2024-06-15")

    # CSV style: separate types
    c3 = CashTransaction(account_id=acc.id, symbol="--", description="Margin Interest (Paid CSV)", 
                         date_time="2024-07-01", settle_date="2024-07-01", amount=Decimal("-30.00"), 
                         type="Broker Interest Paid", currency="EUR", fx_rate_to_base=Decimal("1.0"),
                         report_date="2024-07-01")
    
    c4 = CashTransaction(account_id=acc.id, symbol="--", description="Broker Interest (Received CSV)", 
                         date_time="2024-07-15", settle_date="2024-07-15", amount=Decimal("20.00"), 
                         type="Broker Interest Received", currency="EUR", fx_rate_to_base=Decimal("1.0"),
                         report_date="2024-07-15")

    db_session.add_all([c1, c2, c3, c4])
    db_session.commit()

    # 2. Run Aggregator
    service = TaxAggregatorService(db_session)
    report = service.generate_report("U8888888", 2024)

    # 3. Assertions
    # Line 7 should include received interest: 10 + 20 = 30
    assert report.kap_line_7_kapitalertraege == Decimal("30.00")
    
    # Informational field should include absolute paid interest: 50 + 30 = 80
    assert report.margin_interest_paid == Decimal("80.00")

def test_generate_combined_report_two_accounts(db_session):
    # 1. Setup 2 Accounts
    acc_a = Account(account_id="U_ACCT_A")
    acc_b = Account(account_id="U_ACCT_B")
    db_session.add_all([acc_a, acc_b])
    db_session.commit()

    # 2. Add data for Account A
    # Gain: +300 in Aktien
    t_a = Trade(ib_trade_id="T_A", account_id=acc_a.id, symbol="AAPL", asset_category="STK", 
                description="Apple Inc",
                trade_date="2024-01-01", settle_date="2024-01-03", currency="EUR", 
                fx_rate_to_base=Decimal("1.0"), quantity=Decimal("-10"), trade_price=Decimal("130"), 
                proceeds=Decimal("1300"), buy_sell="SELL")
    db_session.add(t_a)
    db_session.commit()
    g_a = Gain(sell_trade_id=t_a.id, buy_lot_id=100, quantity_matched=10, tax_year=2024, 
               proceeds=Decimal("1300"), cost_basis_matched=Decimal("1000"), realized_pnl=Decimal("300"), tax_pool="Aktien")
    # Dividend for A: 100 USD * 0.9 = 90 EUR
    c_a = CashTransaction(account_id=acc_a.id, symbol="AAPL", description="Dividend", 
                          date_time="2024-05-01", settle_date="2024-05-03", amount=Decimal("100.00"), 
                          type="Dividends", currency="USD", fx_rate_to_base=Decimal("0.9"),
                          report_date="2024-05-01")
    db_session.add_all([g_a, c_a])

    # 3. Add data for Account B
    # Gain: +200 in Aktien
    t_b = Trade(ib_trade_id="T_B", account_id=acc_b.id, symbol="MSFT", asset_category="STK", 
                description="Microsoft Corp",
                trade_date="2024-02-01", settle_date="2024-02-03", currency="EUR", 
                fx_rate_to_base=Decimal("1.0"), quantity=Decimal("-5"), trade_price=Decimal("240"), 
                proceeds=Decimal("1200"), buy_sell="SELL")
    db_session.add(t_b)
    db_session.commit()
    g_b = Gain(sell_trade_id=t_b.id, buy_lot_id=200, quantity_matched=5, tax_year=2024, 
               proceeds=Decimal("1200"), cost_basis_matched=Decimal("1000"), realized_pnl=Decimal("200"), tax_pool="Aktien")
    # Dividend for B: 50 EUR * 1.0 = 50 EUR
    c_b = CashTransaction(account_id=acc_b.id, symbol="MSFT", description="Dividend", 
                          date_time="2024-06-01", settle_date="2024-06-03", amount=Decimal("50.00"), 
                          type="Dividends", currency="EUR", fx_rate_to_base=Decimal("1.0"),
                          report_date="2024-06-01")
    db_session.add_all([g_b, c_b])
    db_session.commit()

    # 4. Run Combined Aggregator
    service = TaxAggregatorService(db_session)
    combined = service.generate_combined_report(["U_ACCT_A", "U_ACCT_B"], 2024)

    # 5. Assertions
    assert len(combined.account_ids) == 2
    assert len(combined.per_account_reports) == 2
    
    # Combined KAP Line 7: 90 + 50 = 140
    assert combined.kap_line_7_kapitalertraege == Decimal("140.00")
    # Combined KAP Line 8: 300 + 200 = 500
    assert combined.kap_line_8_gewinne_aktien == Decimal("500.00")
    # Total PnL: 300 + 200 = 500
    assert combined.total_realized_pnl == Decimal("500.00")

    # Verify per-account breakdowns
    report_a = next(r for r in combined.per_account_reports if r.account_id == "U_ACCT_A")
    assert report_a.kap_line_8_gewinne_aktien == Decimal("300.00")
    assert report_a.kap_line_7_kapitalertraege == Decimal("90.00")

    report_b = next(r for r in combined.per_account_reports if r.account_id == "U_ACCT_B")
    assert report_b.kap_line_8_gewinne_aktien == Decimal("200.00")
    assert report_b.kap_line_7_kapitalertraege == Decimal("50.00")
