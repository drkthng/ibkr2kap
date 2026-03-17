import pytest
from decimal import Decimal
from datetime import date
from unittest.mock import MagicMock

from ibkr_tax.models.database import Account, Trade, FIFOLot, Gain, CashTransaction
from ibkr_tax.services.pipeline import run_import
from ibkr_tax.services.fifo_runner import FIFORunner
from ibkr_tax.services.corporate_actions import CorporateActionEngine
from ibkr_tax.services.tax_aggregator import TaxAggregatorService
from ibkr_tax.schemas.ibkr import AccountSchema, TradeSchema, CashTransactionSchema, OptionEAECreate, CorporateActionSchema

def test_full_multi_year_e2e(db_session, monkeypatch):
    """
    Complete End-to-End integration test covering:
    - Multi-year imports
    - Options (Expiration & Exercise)
    - Corporate Actions (Stock Split)
    - FIFO matching across split-adjusted lots
    - Tax Aggregation (Anlage KAP)
    """
    account_id = "U_E2E_TEST"
    
    # --- 2023: Initial Positions ---
    # 1. Buy 100 AAPL
    # 2. Buy 1 MSFT Call (to be exercised later)
    # 3. Sell 1 SPX Put (to expire OTM)
    
    mock_parser_2023 = MagicMock()
    mock_parser_2023.parse_all.return_value = {
        "accounts": [AccountSchema(account_id=account_id, currency="EUR")],
        "trades": [
            TradeSchema(
                ib_trade_id="T2023_1", account_id=account_id, asset_category="STK", symbol="AAPL",
                description="Apple Inc", trade_date=date(2023, 1, 10), settle_date=date(2023, 1, 12),
                currency="USD", fx_rate_to_base=Decimal("0.9"), quantity=Decimal("100"),
                trade_price=Decimal("150"), proceeds=Decimal("-15000"), buy_sell="BUY", open_close_indicator="O"
            ),
            TradeSchema(
                ib_trade_id="T2023_2", account_id=account_id, asset_category="OPT", symbol="MSFT 240621C00400000",
                description="MSFT Jun 2024 400 Call", trade_date=date(2023, 5, 20), settle_date=date(2023, 5, 22),
                currency="USD", fx_rate_to_base=Decimal("0.9"), quantity=Decimal("1"),
                trade_price=Decimal("10"), proceeds=Decimal("-1000"), buy_sell="BUY", open_close_indicator="O"
            ),
            TradeSchema(
                ib_trade_id="T2023_3", account_id=account_id, asset_category="OPT", symbol="SPX 231215P04500000",
                description="SPX Dec 2023 4500 Put", trade_date=date(2023, 10, 1), settle_date=date(2023, 10, 3),
                currency="USD", fx_rate_to_base=Decimal("0.9"), quantity=Decimal("-1"),
                trade_price=Decimal("50"), proceeds=Decimal("5000"), buy_sell="SELL", open_close_indicator="O"
            )
        ],
        "cash_transactions": [],
        "option_eae": [
             OptionEAECreate(
                 account_id=account_id, currency="USD",
                 symbol="SPX 231215P04500000", date=date(2023, 12, 15), transaction_type="Expiration", 
                 quantity=Decimal("-1"), multiplier=Decimal("100"), strike=Decimal("4500"), 
                 underlying_symbol="SPX", fx_rate_to_base=Decimal("0.9"),
                 expiry=date(2023, 12, 15), put_call="P"
             )
        ]
    }
    
    monkeypatch.setattr("ibkr_tax.services.pipeline.FlexXMLParser", lambda **kwargs: mock_parser_2023)
    
    # Import 2023
    run_import("2023.xml", db_session, file_type="xml")
    
    # Verify 2023 Status
    aggregator = TaxAggregatorService(db_session)
    report_2023 = aggregator.generate_report(account_id, 2023)
    
    # SPX Put expired -> Premium received was 5000 USD * 0.9 = 4500 EUR gain in Termingeschäfte
    assert report_2023.kap_line_10_termingeschaefte == Decimal("4500.00")
    assert report_2023.total_realized_pnl == Decimal("4500.00")

    # --- 2024: Corporate Actions & Exercise & Partial Exit ---
    # 1. AAPL Split 2:1 on 2024-03-01
    # 2. MSFT Call Exercise on 2024-06-21 (Delivers 100 MSFT @ 400)
    # 3. Sell 100 AAPL (out of 200) @ 100 on 2024-08-01
    
    # MSFT Exercise Import
    mock_parser_2024 = MagicMock()
    # The exercise deliverable (stock trade)
    # Premium was -1000 USD. Stock price is 400. 
    # OptionEngine should adjust proceeds from -40000 to -41000.
    mock_parser_2024.parse_all.return_value = {
        "accounts": [], # Already exists
        "trades": [
            TradeSchema(
                ib_trade_id="T2024_1", account_id=account_id, asset_category="STK", symbol="MSFT",
                description="Microsoft Corp", trade_date=date(2024, 6, 21), settle_date=date(2024, 6, 23),
                currency="USD", fx_rate_to_base=Decimal("0.9"), quantity=Decimal("100"),
                trade_price=Decimal("400"), proceeds=Decimal("-40000"), buy_sell="BUY", open_close_indicator="O"
            ),
            TradeSchema(
                ib_trade_id="T2024_2", account_id=account_id, asset_category="STK", symbol="AAPL",
                description="Apple Inc", trade_date=date(2024, 8, 1), settle_date=date(2024, 8, 3),
                currency="USD", fx_rate_to_base=Decimal("0.9"), quantity=Decimal("-100"),
                trade_price=Decimal("100"), proceeds=Decimal("10000"), buy_sell="SELL", open_close_indicator="C"
            )
        ],
        "cash_transactions": [],
        "option_eae": [
            OptionEAECreate(
                account_id=account_id, currency="USD",
                symbol="MSFT 240621C00400000", date=date(2024, 6, 21), transaction_type="Exercise", 
                quantity=Decimal("1"), multiplier=Decimal("100"), strike=Decimal("400"), 
                underlying_symbol="MSFT", fx_rate_to_base=Decimal("0.9"),
                expiry=date(2024, 6, 21), put_call="C"
            )
        ],
        "corporate_actions": [
            CorporateActionSchema(
                account_id=account_id, symbol="AAPL", action_type="RS", 
                date=date(2024, 3, 1), report_date=date(2024, 3, 1),
                quantity=Decimal("100"), currency="USD", transaction_id="CA_SPLIT_1",
                description="AAPL(US0378331005) SPLIT 2 FOR 1"
            )
        ]
    }
    
    monkeypatch.setattr("ibkr_tax.services.pipeline.FlexXMLParser", lambda **kwargs: mock_parser_2024)
    run_import("2024.xml", db_session, file_type="xml")
    
    # Verify 2024 Status
    report_2024 = aggregator.generate_report(account_id, 2024)
    
    # AAPL Profit:
    # Buy: 100 @ 150 = 15000 USD.
    # Split: 200 @ 75 = 15000 USD.
    # Sell: 100 @ 100 = 10000 USD.
    # Cost for 100: 7500 USD.
    # Profit: 2500 USD * 0.9 = 2250 EUR.
    assert report_2024.kap_line_8_gewinne_aktien == Decimal("2250.00")
    
    # MSFT Position check in DB
    msft_lot = db_session.query(FIFOLot).filter(FIFOLot.symbol == "MSFT").first()
    # Cost basis should be (40000 + 1000) * 0.9 = 41000 * 0.9 = 36900 EUR
    assert msft_lot.cost_basis_total == Decimal("36900.00")
    
    # --- 2025: Final Exit & Dividends ---
    # 1. Sell 100 MSFT @ 450
    # 2. Sell 100 AAPL (remaining) @ 120
    # 3. Dividend MSFT 50 USD
    
    mock_parser_2025 = MagicMock()
    mock_parser_2025.parse_all.return_value = {
        "accounts": [],
        "trades": [
            TradeSchema(
                ib_trade_id="T2025_1", account_id=account_id, asset_category="STK", symbol="MSFT",
                description="Microsoft Corp", trade_date=date(2025, 1, 10), settle_date=date(2025, 1, 12),
                currency="USD", fx_rate_to_base=Decimal("0.9"), quantity=Decimal("-100"),
                trade_price=Decimal("450"), proceeds=Decimal("45000"), buy_sell="SELL", open_close_indicator="C"
            ),
            TradeSchema(
                ib_trade_id="T2025_2", account_id=account_id, asset_category="STK", symbol="AAPL",
                description="Apple Inc", trade_date=date(2025, 2, 1), settle_date=date(2025, 2, 3),
                currency="USD", fx_rate_to_base=Decimal("0.9"), quantity=Decimal("-100"),
                trade_price=Decimal("120"), proceeds=Decimal("12000"), buy_sell="SELL", open_close_indicator="C"
            )
        ],
        "cash_transactions": [
            CashTransactionSchema(
                account_id=account_id, symbol="MSFT", description="Microsoft Dividend", 
                date_time="2025-03-01 10:00:00", settle_date=date(2025, 3, 3),
                amount=Decimal("50"), type="Dividends", currency="USD",
                fx_rate_to_base=Decimal("0.9"), report_date=date(2025, 3, 1)
            )
        ]
    }
    
    monkeypatch.setattr("ibkr_tax.services.pipeline.FlexXMLParser", lambda **kwargs: mock_parser_2025)
    run_import("2025.xml", db_session, file_type="xml")
    
    report_2025 = aggregator.generate_report(account_id, 2025)
    
    # MSFT Profit:
    # Sell 45000 USD * 0.9 = 40500 EUR.
    # Cost 36900 EUR.
    # Profit = 3600 EUR. (Sonstige, because MSFT is STK but handled as general pool if not specifically AAPL? 
    # No, all STK are in Line 8/9 in this app's logic usually if they are defined as "Aktien")
    # Actually, TaxAggregator defines pools. Let's check what it uses for MSFT.
    
    # AAPL Profit (remaining 100):
    # Sell 12000 USD * 0.9 = 10800 EUR.
    # Cost 7500 USD * 0.9 = 6750 EUR.
    # Profit = 4050 EUR.
    
    # Total Line 8 (Aktien): 4050 (AAPL) + 3600 (MSFT if STK) = 7650?
    # Actually, let's verify line 7 vs line 8.
    
    # Dividend: 50 USD * 0.9 = 45 EUR.
    assert report_2025.kap_line_7_kapitalertraege == Decimal("45.00")
    assert report_2025.kap_line_8_gewinne_aktien == Decimal("7650.00")
    
    print("E2E Test Passed Successfully!")
