"""Tests for TransferEngine and transfer parsing in FlexXMLParser."""
import pytest
from decimal import Decimal

from ibkr_tax.models.database import Account, Trade, Transfer, FIFOLot, Gain
from ibkr_tax.services.transfer_engine import TransferEngine
from ibkr_tax.services.fifo import FIFOEngine
from ibkr_tax.services.flex_parser import FlexXMLParser


# ─── Fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture
def account(db_session):
    acc = Account(account_id="U7230673", currency="EUR")
    db_session.add(acc)
    db_session.flush()
    return acc


@pytest.fixture
def counterparty_account(db_session):
    acc = Account(account_id="U7330779", currency="EUR")
    db_session.add(acc)
    db_session.flush()
    return acc


def _make_stock_transfer_in(account, symbol="AEHR", quantity="22",
                             settle_date="2022-11-22",
                             position_amount_in_base="514.73874452"):
    """Helper to create an IN-direction stock transfer."""
    return Transfer(
        account_id=account.id,
        symbol=symbol,
        description=f"{symbol} TRANSFER",
        currency="USD",
        fx_rate_to_base=Decimal("0.97643"),
        transfer_type="INTERNAL",
        direction="IN",
        quantity=Decimal(quantity),
        transfer_date=settle_date,
        settle_date=settle_date,
        counterparty_account="U7330779",
        position_amount=Decimal("527.164"),
        position_amount_in_base=Decimal(position_amount_in_base),
        cash_transfer=Decimal("0"),
        isin="US00760J1088",
    )


def _make_stock_transfer_out(account, symbol="AEHR", quantity="22",
                              settle_date="2022-11-22"):
    """Helper to create an OUT-direction stock transfer."""
    return Transfer(
        account_id=account.id,
        symbol=symbol,
        description=f"TRANSFER OUT {symbol}",
        currency="USD",
        fx_rate_to_base=Decimal("0.97643"),
        transfer_type="INTERNAL",
        direction="OUT",
        quantity=Decimal(f"-{quantity}"),
        transfer_date=settle_date,
        settle_date=settle_date,
        counterparty_account="U7230673",
        position_amount=Decimal("-527.164"),
        position_amount_in_base=Decimal("-514.73874452"),
        cash_transfer=Decimal("0"),
        isin="US00760J1088",
    )


def _make_cash_transfer(account, settle_date="2023-03-27"):
    """Helper to create a cash-only transfer (quantity=0, symbol='--')."""
    return Transfer(
        account_id=account.id,
        symbol="--",
        description="TRANSFER FROM U7330779 TO U7230673",
        currency="EUR",
        fx_rate_to_base=Decimal("1"),
        transfer_type="INTERNAL",
        direction="IN",
        quantity=Decimal("0"),
        transfer_date=settle_date,
        settle_date=settle_date,
        counterparty_account="U7330779",
        position_amount=Decimal("0"),
        position_amount_in_base=Decimal("0"),
        cash_transfer=Decimal("7000"),
        isin=None,
    )


# ─── TransferEngine Tests ──────────────────────────────────────────────────

class TestTransferEngineStockIN:
    """Stock transfer IN should create a FIFOLot."""

    def test_creates_fifo_lot(self, db_session, account):
        transfer = _make_stock_transfer_in(account)
        db_session.add(transfer)
        db_session.flush()

        engine = TransferEngine(db_session)
        lots_created = engine.process_transfers(account.id)

        assert lots_created == 1
        lot = db_session.query(FIFOLot).filter_by(transfer_id=transfer.id).first()
        assert lot is not None
        assert lot.symbol == "AEHR"
        assert lot.asset_category == "STK"
        assert lot.original_quantity == Decimal("22")
        assert lot.remaining_quantity == Decimal("22")
        assert lot.trade_id is None
        assert lot.corporate_action_id is None

    def test_cost_basis_from_position_amount_in_base(self, db_session, account):
        transfer = _make_stock_transfer_in(account)
        db_session.add(transfer)
        db_session.flush()

        engine = TransferEngine(db_session)
        engine.process_transfers(account.id)

        lot = db_session.query(FIFOLot).filter_by(transfer_id=transfer.id).one()
        # Cost basis should be positionAmountInBase (EUR)
        # Note: FIFOLot.cost_basis_total is Numeric(18,4) so precision is limited
        assert abs(lot.cost_basis_total - Decimal("514.7387")) < Decimal("0.001")
        expected_per_share = lot.cost_basis_total / Decimal("22")
        assert abs(lot.cost_basis_per_share - expected_per_share) < Decimal("0.001")

    def test_settle_date_preserved(self, db_session, account):
        transfer = _make_stock_transfer_in(account, settle_date="2022-11-22")
        db_session.add(transfer)
        db_session.flush()

        engine = TransferEngine(db_session)
        engine.process_transfers(account.id)

        lot = db_session.query(FIFOLot).filter_by(transfer_id=transfer.id).one()
        assert lot.settle_date == "2022-11-22"


class TestTransferEngineOUT:
    """Stock transfer OUT should NOT create a FIFOLot."""

    def test_out_direction_creates_no_lot(self, db_session, account):
        transfer = _make_stock_transfer_out(account)
        db_session.add(transfer)
        db_session.flush()

        engine = TransferEngine(db_session)
        lots_created = engine.process_transfers(account.id)

        assert lots_created == 0
        lot = db_session.query(FIFOLot).filter_by(transfer_id=transfer.id).first()
        assert lot is None


class TestTransferEngineCashOnly:
    """Cash-only transfers (qty=0, symbol='--') should NOT create FIFOLots."""

    def test_cash_transfer_creates_no_lot(self, db_session, account):
        transfer = _make_cash_transfer(account)
        db_session.add(transfer)
        db_session.flush()

        engine = TransferEngine(db_session)
        lots_created = engine.process_transfers(account.id)

        assert lots_created == 0
        lots = db_session.query(FIFOLot).all()
        assert len(lots) == 0


class TestTransferEngineIdempotency:
    """Processing the same transfers twice should only create lots once."""

    def test_idempotent_processing(self, db_session, account):
        transfer = _make_stock_transfer_in(account)
        db_session.add(transfer)
        db_session.flush()

        engine = TransferEngine(db_session)
        first_run = engine.process_transfers(account.id)
        second_run = engine.process_transfers(account.id)

        assert first_run == 1
        assert second_run == 0
        lots = db_session.query(FIFOLot).filter_by(transfer_id=transfer.id).all()
        assert len(lots) == 1


class TestTransferFIFOIntegration:
    """Transferred lots should participate in FIFO sell matching."""

    def test_transferred_lot_matched_on_sell(self, db_session, account):
        # 1. Create stock transfer: 22 AEHR arrive at cost 514.74 EUR
        transfer = _make_stock_transfer_in(account, quantity="22",
                                           position_amount_in_base="514.74")
        db_session.add(transfer)
        db_session.flush()

        # Process transfer to create FIFOLot
        transfer_engine = TransferEngine(db_session)
        transfer_engine.process_transfers(account.id)

        lot = db_session.query(FIFOLot).filter_by(transfer_id=transfer.id).one()
        assert lot.remaining_quantity == Decimal("22")

        # 2. Sell 10 AEHR at $30 with EUR fx rate 0.95
        sell = Trade(
            ib_trade_id="SELL_AEHR",
            account_id=account.id,
            asset_category="STK",
            symbol="AEHR",
            description="AEHR TEST SYSTEMS",
            trade_date="2023-01-10",
            settle_date="2023-01-12",
            currency="USD",
            fx_rate_to_base=Decimal("0.95"),
            quantity=Decimal("-10"),
            trade_price=Decimal("30"),
            proceeds=Decimal("300"),
            ib_commission=Decimal("-1"),
            buy_sell="SELL",
        )
        db_session.add(sell)
        db_session.flush()

        fifo_engine = FIFOEngine(db_session)
        fifo_engine.process_trade(sell)

        # 3. Verify FIFO matching
        db_session.refresh(lot)
        assert lot.remaining_quantity == Decimal("12")  # 22 - 10

        gain = db_session.query(Gain).filter_by(sell_trade_id=sell.id).one()
        assert gain.quantity_matched == Decimal("10")
        assert gain.buy_lot_id == lot.id
        assert gain.tax_pool == "Aktien"

        # Verify cost basis proportional: 514.74 * (10/22)
        expected_cost = Decimal("514.74") * Decimal("10") / Decimal("22")
        assert abs(gain.cost_basis_matched - expected_cost) < Decimal("0.01")


# ─── Flex Parser Transfer Parsing Tests ─────────────────────────────────────

STOCK_TRANSFER_XML = """<?xml version="1.0" encoding="UTF-8"?>
<FlexQueryResponse queryName="test" type="AF">
<FlexStatements count="1">
<FlexStatement accountId="U7230673" toDate="20221231" fromDate="20220101">
<AccountInformation accountId="U7230673" currency="EUR" />
<Trades />
<CashTransactions />
<Transfers>
<Transfer accountId="U7230673" currency="USD" fxRateToBase="0.97643"
    symbol="AEHR" description="AEHR TEST SYSTEMS"
    securityID="US00760J1088" securityIDType="ISIN" isin="US00760J1088"
    type="INTERNAL" direction="IN" quantity="22" transferPrice="0"
    dateTime="20221121;102932" settleDate="20221122"
    account="U7330779" positionAmount="527.164" positionAmountInBase="514.73874452"
    pnlAmount="-36.553858" pnlAmountInBase="-36.553858" cashTransfer="0"
    deliveryType="" />
</Transfers>
</FlexStatement>
</FlexStatements>
</FlexQueryResponse>"""


CASH_TRANSFER_XML = """<?xml version="1.0" encoding="UTF-8"?>
<FlexQueryResponse queryName="test" type="AF">
<FlexStatements count="1">
<FlexStatement accountId="U7330779" toDate="20231231" fromDate="20230101">
<AccountInformation accountId="U7330779" currency="EUR" />
<Trades />
<CashTransactions />
<Transfers>
<Transfer accountId="U7330779" currency="EUR" fxRateToBase="1"
    symbol="--" description="TRANSFER FROM U7330779 TO U7230673"
    securityID="" securityIDType="" isin=""
    type="INTERNAL" direction="OUT" quantity="0" transferPrice="0"
    dateTime="20230327;034034" settleDate="20230327"
    account="U7230673" positionAmount="0" positionAmountInBase="0"
    pnlAmount="0" pnlAmountInBase="0" cashTransfer="-7000"
    deliveryType="" />
</Transfers>
</FlexStatement>
</FlexStatements>
</FlexQueryResponse>"""


class TestFlexParserTransfers:
    """Test that get_transfers() correctly parses transfer XML."""

    def test_parse_stock_transfer(self):
        parser = FlexXMLParser(xml_content=STOCK_TRANSFER_XML)
        transfers = parser.get_transfers()

        assert len(transfers) == 1
        t = transfers[0]
        assert t.account_id == "U7230673"
        assert t.symbol == "AEHR"
        assert t.direction == "IN"
        assert t.quantity == Decimal("22")
        assert t.transfer_type == "INTERNAL"
        assert t.counterparty_account == "U7330779"
        assert t.position_amount == Decimal("527.164")
        assert t.position_amount_in_base == Decimal("514.73874452")
        assert t.cash_transfer == Decimal("0")
        assert t.isin == "US00760J1088"
        assert t.is_stock_transfer is True

    def test_parse_cash_transfer(self):
        parser = FlexXMLParser(xml_content=CASH_TRANSFER_XML)
        transfers = parser.get_transfers()

        assert len(transfers) == 1
        t = transfers[0]
        assert t.symbol == "--"
        assert t.direction == "OUT"
        assert t.quantity == Decimal("0")
        assert t.cash_transfer == Decimal("-7000")
        assert t.is_stock_transfer is False

    def test_parse_all_includes_transfers(self):
        parser = FlexXMLParser(xml_content=STOCK_TRANSFER_XML)
        result = parser.parse_all()

        assert "transfers" in result
        assert len(result["transfers"]) == 1

    def test_transfers_not_in_unmapped_entities(self):
        parser = FlexXMLParser(xml_content=STOCK_TRANSFER_XML)
        warnings = parser.get_unmapped_entities()

        # Transfers should not appear as unmapped
        unmapped_tags = [w["entity"] for w in warnings]
        assert "Transfers" not in unmapped_tags
