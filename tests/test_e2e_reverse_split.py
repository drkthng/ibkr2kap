"""E2E test: DEC 1-for-20 reverse split with symbol/ISIN rename.

Verifies that the full pipeline (FIFORunner with grouped RS records)
correctly consolidates 40,000 DEC shares into 2,000 shares while
preserving total cost basis (German tax-neutral consolidation).
"""

import pytest
from decimal import Decimal
from ibkr_tax.models.database import Account, Trade, CorporateAction, FIFOLot
from ibkr_tax.services.fifo_runner import FIFORunner


@pytest.fixture
def dec_scenario(db_session):
    """Set up a realistic DEC reverse split scenario matching the 2023 XML."""
    acc = Account(account_id="U7230673", currency="EUR")
    db_session.add(acc)
    db_session.flush()

    # === DEC Trades (before reverse split) ===
    # Two buys totaling 40,000 shares under original symbol "DEC"
    buy1 = Trade(
        ib_trade_id="DEC_BUY1", account_id=acc.id, asset_category="STK",
        symbol="DEC", description="DIVERSIFIED ENERGY",
        trade_date="2023-11-01", settle_date="2023-11-03",
        currency="GBP", fx_rate_to_base=Decimal("1.15"),
        quantity=Decimal("5000"), trade_price=Decimal("0.80"),
        proceeds=Decimal("-4000"), ib_commission=Decimal("-10"),
        buy_sell="BUY",
    )
    buy2 = Trade(
        ib_trade_id="DEC_BUY2", account_id=acc.id, asset_category="STK",
        symbol="DEC", description="DIVERSIFIED ENERGY",
        trade_date="2023-11-15", settle_date="2023-11-17",
        currency="GBP", fx_rate_to_base=Decimal("1.15"),
        quantity=Decimal("35000"), trade_price=Decimal("0.75"),
        proceeds=Decimal("-26250"), ib_commission=Decimal("-50"),
        buy_sell="BUY",
    )
    db_session.add_all([buy1, buy2])
    db_session.flush()

    # === DEC Reverse Split Corporate Actions ===
    # 4 RS records as seen in IBKR's 2023 XML export
    # Positive records: new shares under DEC with new ISIN
    ca1 = CorporateAction(
        account_id=acc.id, symbol="DEC", parent_symbol="DEC",
        action_type="RS", date="2023-12-04", report_date="2023-12-05",
        quantity=Decimal("250"), value=Decimal("0"),
        isin="GB00BQHP5P93", currency="GBP",
        transaction_id="RS_TX1",
        description="DEC(GB00BYX7JT74) SPLIT 1 FOR 20 (DEC, DIVERSIFIED ENERGY COMPANY PLC, GB00BQHP5P93)",
        tax_treatment="NEUTRAL_SPLIT",
    )
    ca2 = CorporateAction(
        account_id=acc.id, symbol="DEC", parent_symbol="DEC",
        action_type="RS", date="2023-12-04", report_date="2023-12-05",
        quantity=Decimal("1750"), value=Decimal("0"),
        isin="GB00BQHP5P93", currency="GBP",
        transaction_id="RS_TX2",
        description="DEC(GB00BYX7JT74) SPLIT 1 FOR 20 (DEC, DIVERSIFIED ENERGY COMPANY PLC, GB00BQHP5P93)",
        tax_treatment="NEUTRAL_SPLIT",
    )
    # Negative records: old shares removed under DEC.OLD with old ISIN
    ca3 = CorporateAction(
        account_id=acc.id, symbol="DEC.OLD", parent_symbol="DEC",
        action_type="RS", date="2023-12-04", report_date="2023-12-05",
        quantity=Decimal("-5000"), value=Decimal("0"),
        isin="GB00BYX7JT74", currency="GBP",
        transaction_id="RS_TX3",
        description="DEC(GB00BYX7JT74) SPLIT 1 FOR 20 (DEC, DIVERSIFIED ENERGY COMPANY PLC, GB00BQHP5P93)",
        tax_treatment="NEUTRAL_SPLIT",
    )
    ca4 = CorporateAction(
        account_id=acc.id, symbol="DEC.OLD", parent_symbol="DEC",
        action_type="RS", date="2023-12-04", report_date="2023-12-05",
        quantity=Decimal("-35000"), value=Decimal("0"),
        isin="GB00BYX7JT74", currency="GBP",
        transaction_id="RS_TX4",
        description="DEC(GB00BYX7JT74) SPLIT 1 FOR 20 (DEC, DIVERSIFIED ENERGY COMPANY PLC, GB00BQHP5P93)",
        tax_treatment="NEUTRAL_SPLIT",
    )
    db_session.add_all([ca1, ca2, ca3, ca4])

    # === Post-split trade ===
    # Buy 200 more DEC shares after the consolidation (new ISIN)
    buy_post = Trade(
        ib_trade_id="DEC_BUY3", account_id=acc.id, asset_category="STK",
        symbol="DEC", description="DIVERSIFIED ENERGY",
        trade_date="2023-12-19", settle_date="2023-12-21",
        currency="GBP", fx_rate_to_base=Decimal("1.15"),
        quantity=Decimal("200"), trade_price=Decimal("15.00"),
        proceeds=Decimal("-3000"), ib_commission=Decimal("-5"),
        buy_sell="BUY",
    )
    db_session.add(buy_post)
    db_session.flush()

    return acc


class TestE2EReverseSplit:
    """End-to-end tests for the DEC 1-for-20 reverse split."""

    def test_lots_consolidated_after_reverse_split(self, db_session, dec_scenario):
        """40,000 old shares become 2,000 new shares across 2 lots."""
        acc = dec_scenario

        runner = FIFORunner(db_session)
        runner.run_for_account(acc.id)

        lots = (
            db_session.query(FIFOLot)
            .filter(FIFOLot.symbol == "DEC")
            .order_by(FIFOLot.settle_date)
            .all()
        )

        # 3 lots: 2 pre-split (adjusted) + 1 post-split
        assert len(lots) == 3

        # Pre-split lot 1: 5000 * (1/20) = 250 shares
        assert lots[0].remaining_quantity == Decimal("250")
        assert lots[0].symbol == "DEC"

        # Pre-split lot 2: 35000 * (1/20) = 1750 shares
        assert lots[1].remaining_quantity == Decimal("1750")
        assert lots[1].symbol == "DEC"

        # Post-split lot: 200 shares (no adjustment)
        assert lots[2].remaining_quantity == Decimal("200")

    def test_cost_basis_total_preserved(self, db_session, dec_scenario):
        """Total cost basis for each lot must remain unchanged after consolidation."""
        acc = dec_scenario

        runner = FIFORunner(db_session)
        runner.run_for_account(acc.id)

        lots = (
            db_session.query(FIFOLot)
            .filter(FIFOLot.symbol == "DEC")
            .order_by(FIFOLot.settle_date)
            .all()
        )

        # Lot 1: (abs(-4000) + abs(-10)) * FX 1.15 = 4010 * 1.15 = 4611.50
        assert lots[0].cost_basis_total == Decimal("4611.5000")

        # Lot 2: (abs(-26250) + abs(-50)) * FX 1.15 = 26300 * 1.15 = 30245.00
        assert lots[1].cost_basis_total == Decimal("30245.0000")

        # Post-split lot: (abs(-3000) + abs(-5)) * FX 1.15 = 3005 * 1.15 = 3455.75
        assert lots[2].cost_basis_total == Decimal("3455.7500")

    def test_cost_basis_per_share_recalculated(self, db_session, dec_scenario):
        """Per-share cost basis increases proportionally with consolidation."""
        acc = dec_scenario

        runner = FIFORunner(db_session)
        runner.run_for_account(acc.id)

        lots = (
            db_session.query(FIFOLot)
            .filter(FIFOLot.symbol == "DEC")
            .order_by(FIFOLot.settle_date)
            .all()
        )

        # Lot 1: 4611.50 / 250 = 18.446 per share
        expected_1 = round(Decimal("4611.5000") / Decimal("250"), 4)
        assert round(lots[0].cost_basis_per_share, 4) == expected_1

        # Lot 2: 30245.00 / 1750 ≈ 17.2829 per share
        expected_2 = round(Decimal("30245.0000") / Decimal("1750"), 4)
        assert round(lots[1].cost_basis_per_share, 4) == expected_2

    def test_total_shares_after_consolidation(self, db_session, dec_scenario):
        """Total shares = 250 + 1750 + 200 = 2200."""
        acc = dec_scenario

        runner = FIFORunner(db_session)
        runner.run_for_account(acc.id)

        total = sum(
            lot.remaining_quantity
            for lot in db_session.query(FIFOLot)
            .filter(FIFOLot.symbol == "DEC")
            .all()
        )

        # 2000 (consolidated) + 200 (post-split buy) = 2200
        assert total == Decimal("2200")
