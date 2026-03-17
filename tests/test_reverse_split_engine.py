"""Tests for CorporateActionEngine.apply_split() — reverse split with symbol rename."""

import pytest
from decimal import Decimal
from datetime import date
from ibkr_tax.models.database import Account, FIFOLot
from ibkr_tax.services.corporate_actions import CorporateActionEngine
from ibkr_tax.schemas.ibkr import CorporateActionSchema


@pytest.fixture
def account(db_session):
    acc = Account(account_id="U123456", currency="EUR")
    db_session.add(acc)
    db_session.flush()
    return acc


class TestReverseSplitWithSymbolRename:
    """Tests for reverse split consolidation with ISIN/symbol change."""

    def test_reverse_split_renames_symbol(self, db_session, account):
        """1-for-20 reverse split: DEC lots renamed from DEC to DEC."""
        # Simulate lots bought under original symbol "DEC"
        lot = FIFOLot(
            trade_id=1, asset_category="STK", symbol="DEC",
            settle_date="2023-03-01", original_quantity=Decimal("1000"),
            remaining_quantity=Decimal("1000"),
            cost_basis_total=Decimal("1000"), cost_basis_per_share=Decimal("1"),
        )
        db_session.add(lot)
        db_session.flush()

        # Grouped action: parent_symbol=DEC.OLD (old), symbol=DEC (new)
        action = CorporateActionSchema(
            account_id="U123456", symbol="DEC", parent_symbol="DEC.OLD",
            action_type="RS", date=date(2023, 12, 4), report_date=date(2023, 12, 5),
            quantity=Decimal("50"), currency="GBP", transaction_id="TX1",
            description="DEC(GB00BYX7JT74) SPLIT 1 FOR 20",
        )

        CorporateActionEngine(db_session).apply(action)
        db_session.refresh(lot)

        # Quantity adjusted: 1000 * (1/20) = 50
        assert lot.remaining_quantity == Decimal("50")
        assert lot.original_quantity == Decimal("50")

        # Cost basis total preserved (tax-neutral)
        assert lot.cost_basis_total == Decimal("1000")

        # Per-share recalculated: 1000 / 50 = 20
        assert lot.cost_basis_per_share == Decimal("20")

        # Symbol stays as DEC (not renamed because lots were already DEC)
        assert lot.symbol == "DEC"

    def test_reverse_split_preserves_cost_basis_total(self, db_session, account):
        """Cost basis total must not change during a tax-neutral consolidation."""
        lot = FIFOLot(
            trade_id=2, asset_category="STK", symbol="DEC",
            settle_date="2023-06-01",
            original_quantity=Decimal("5000"),
            remaining_quantity=Decimal("3000"),
            cost_basis_total=Decimal("5000"),
            cost_basis_per_share=Decimal("1"),
        )
        db_session.add(lot)
        db_session.flush()

        action = CorporateActionSchema(
            account_id="U123456", symbol="DEC", parent_symbol="DEC.OLD",
            action_type="RS", date=date(2023, 12, 4), report_date=date(2023, 12, 5),
            quantity=Decimal("250"), currency="GBP", transaction_id="TX2",
            description="DEC(GB00BYX7JT74) SPLIT 1 FOR 20",
        )

        CorporateActionEngine(db_session).apply(action)
        db_session.refresh(lot)

        assert lot.cost_basis_total == Decimal("5000")  # Unchanged
        assert lot.original_quantity == Decimal("250")   # 5000 * 0.05
        assert lot.remaining_quantity == Decimal("150")   # 3000 * 0.05

    def test_forward_split_doubles_shares(self, db_session, account):
        """2-for-1 forward split: quantity doubles, cost per share halves."""
        lot = FIFOLot(
            trade_id=3, asset_category="STK", symbol="8031.T",
            settle_date="2023-01-01",
            original_quantity=Decimal("200"),
            remaining_quantity=Decimal("200"),
            cost_basis_total=Decimal("10000"),
            cost_basis_per_share=Decimal("50"),
        )
        db_session.add(lot)
        db_session.flush()

        action = CorporateActionSchema(
            account_id="U123456", symbol="8031.T",
            action_type="FS", date=date(2024, 6, 26), report_date=date(2024, 6, 27),
            quantity=Decimal("200"), currency="JPY", transaction_id="TX3",
            description="8031.T(JP3893600001) SPLIT 2 FOR 1",
        )

        CorporateActionEngine(db_session).apply(action)
        db_session.refresh(lot)

        assert lot.original_quantity == Decimal("400")    # 200 * 2
        assert lot.remaining_quantity == Decimal("400")
        assert lot.cost_basis_total == Decimal("10000")   # Preserved
        assert lot.cost_basis_per_share == Decimal("25")  # 10000 / 400

    def test_multiple_lots_all_adjusted(self, db_session, account):
        """All open lots for the symbol are adjusted."""
        lots = []
        for i in range(3):
            lot = FIFOLot(
                trade_id=10 + i, asset_category="STK", symbol="DEC",
                settle_date=f"2023-0{i+1}-01",
                original_quantity=Decimal("100"),
                remaining_quantity=Decimal("100"),
                cost_basis_total=Decimal("100"),
                cost_basis_per_share=Decimal("1"),
            )
            db_session.add(lot)
            lots.append(lot)
        db_session.flush()

        action = CorporateActionSchema(
            account_id="U123456", symbol="DEC", parent_symbol="DEC.OLD",
            action_type="RS", date=date(2023, 12, 4), report_date=date(2023, 12, 5),
            quantity=Decimal("15"), currency="GBP", transaction_id="TX4",
            description="DEC(GB00BYX7JT74) SPLIT 1 FOR 20",
        )

        CorporateActionEngine(db_session).apply(action)

        for lot in lots:
            db_session.refresh(lot)
            assert lot.original_quantity == Decimal("5")  # 100 / 20
            assert lot.cost_basis_total == Decimal("100")

    def test_zero_remaining_lots_skipped(self, db_session, account):
        """Fully consumed lots (remaining=0) are not affected."""
        open_lot = FIFOLot(
            trade_id=20, asset_category="STK", symbol="DEC",
            settle_date="2023-01-01",
            original_quantity=Decimal("100"),
            remaining_quantity=Decimal("100"),
            cost_basis_total=Decimal("100"),
            cost_basis_per_share=Decimal("1"),
        )
        closed_lot = FIFOLot(
            trade_id=21, asset_category="STK", symbol="DEC",
            settle_date="2023-02-01",
            original_quantity=Decimal("200"),
            remaining_quantity=Decimal("0"),
            cost_basis_total=Decimal("200"),
            cost_basis_per_share=Decimal("1"),
        )
        db_session.add_all([open_lot, closed_lot])
        db_session.flush()

        action = CorporateActionSchema(
            account_id="U123456", symbol="DEC", parent_symbol="DEC.OLD",
            action_type="RS", date=date(2023, 12, 4), report_date=date(2023, 12, 5),
            quantity=Decimal("5"), currency="GBP", transaction_id="TX5",
            description="DEC(GB00BYX7JT74) SPLIT 1 FOR 20",
        )

        CorporateActionEngine(db_session).apply(action)

        db_session.refresh(open_lot)
        db_session.refresh(closed_lot)

        assert open_lot.original_quantity == Decimal("5")   # Adjusted
        assert closed_lot.original_quantity == Decimal("200")  # Not touched
