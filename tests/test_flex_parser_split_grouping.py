"""Tests for FlexXMLParser.group_split_actions() — split record grouping logic."""

import pytest
from decimal import Decimal
from datetime import date
from ibkr_tax.schemas.ibkr import CorporateActionSchema
from ibkr_tax.services.flex_parser import FlexXMLParser


def _make_action(**kwargs) -> CorporateActionSchema:
    """Helper to build a CorporateActionSchema with sane defaults."""
    defaults = {
        "account_id": "U123",
        "symbol": "TEST",
        "parent_symbol": None,
        "action_type": "RS",
        "date": date(2023, 12, 4),
        "report_date": date(2023, 12, 5),
        "quantity": Decimal("0"),
        "value": Decimal("0"),
        "isin": None,
        "currency": "GBP",
        "transaction_id": "TX1",
        "description": "DEC(GB00BYX7JT74) SPLIT 1 FOR 20",
        "tax_treatment": "NEUTRAL_SPLIT",
    }
    defaults.update(kwargs)
    return CorporateActionSchema(**defaults)


class TestGroupSplitActions:
    """Tests for grouping RS/FS corporate action records."""

    @pytest.fixture
    def parser(self):
        """Create parser with minimal valid XML."""
        xml = '<FlexQueryResponse queryName="test" type="AF"><FlexStatements count="1"><FlexStatement accountId="U123" fromDate="20230101" toDate="20231231" period="" whenGenerated="20260101;000000"><Trades></Trades></FlexStatement></FlexStatements></FlexQueryResponse>'
        return FlexXMLParser(xml_content=xml)

    def test_dec_reverse_split_grouped_to_one_event(self, parser):
        """DEC 1-for-20: 4 RS records (2 positive DEC, 2 negative DEC.OLD) -> 1 grouped event."""
        actions = [
            _make_action(
                symbol="DEC", parent_symbol="DEC", quantity=Decimal("250"),
                isin="GB00BQHP5P93", transaction_id="TX1",
            ),
            _make_action(
                symbol="DEC", parent_symbol="DEC", quantity=Decimal("1750"),
                isin="GB00BQHP5P93", transaction_id="TX2",
            ),
            _make_action(
                symbol="DEC.OLD", parent_symbol="DEC", quantity=Decimal("-5000"),
                isin="GB00BYX7JT74", transaction_id="TX3",
            ),
            _make_action(
                symbol="DEC.OLD", parent_symbol="DEC", quantity=Decimal("-35000"),
                isin="GB00BYX7JT74", transaction_id="TX4",
            ),
        ]

        result = parser.group_split_actions(actions)

        assert len(result) == 1
        event = result[0]
        assert event.symbol == "DEC"           # New symbol
        assert event.parent_symbol == "DEC.OLD"  # Old symbol (for FIFOLot lookup)
        assert event.quantity == Decimal("2000")  # Total new shares
        assert event.action_type == "RS"
        assert event.tax_treatment == "NEUTRAL_SPLIT"

    def test_dec_reverse_split_ratio_is_correct(self, parser):
        """Verify the ratio property derives 1/20 = 0.05 from description."""
        actions = [
            _make_action(symbol="DEC", parent_symbol="DEC", quantity=Decimal("2000")),
            _make_action(symbol="DEC.OLD", parent_symbol="DEC", quantity=Decimal("-40000"), transaction_id="TX2"),
        ]

        result = parser.group_split_actions(actions)
        event = result[0]

        # The ratio property parses "1 FOR 20" from description
        assert event.ratio == Decimal("1") / Decimal("20")

    def test_forward_split_single_record_passthrough(self, parser):
        """A single FS record passes through unchanged."""
        actions = [
            _make_action(
                action_type="FS", symbol="8031.T", parent_symbol="8031.T",
                quantity=Decimal("200"), description="8031.T(JP3893600001) SPLIT 2 FOR 1",
                currency="JPY", transaction_id="TX10",
            ),
        ]

        result = parser.group_split_actions(actions)
        assert len(result) == 1
        assert result[0].symbol == "8031.T"
        assert result[0].quantity == Decimal("200")
        assert result[0].ratio == Decimal("2")

    def test_non_split_actions_preserved(self, parser):
        """SO, RI, DW, DI, ED actions pass through unchanged."""
        so = _make_action(action_type="SO", symbol="LMN", quantity=Decimal("3"), transaction_id="TX20")
        ri = _make_action(action_type="RI", symbol="CSU.RT", quantity=Decimal("1"), transaction_id="TX21")

        result = parser.group_split_actions([so, ri])
        assert len(result) == 2
        assert result[0].action_type == "SO"
        assert result[1].action_type == "RI"

    def test_mixed_split_and_non_split(self, parser):
        """Split actions grouped while non-splits preserved."""
        so = _make_action(action_type="SO", symbol="LMN", quantity=Decimal("3"), transaction_id="TX30")
        rs1 = _make_action(symbol="DEC", parent_symbol="DEC", quantity=Decimal("2000"), transaction_id="TX31")
        rs2 = _make_action(symbol="DEC.OLD", parent_symbol="DEC", quantity=Decimal("-40000"), transaction_id="TX32")

        result = parser.group_split_actions([so, rs1, rs2])
        assert len(result) == 2  # 1 SO + 1 grouped RS

        types = {a.action_type for a in result}
        assert types == {"SO", "RS"}

    def test_same_sign_records_aggregated(self, parser):
        """Multiple positive-only records for the same split are aggregated."""
        actions = [
            _make_action(
                symbol="TEST", parent_symbol="TEST", quantity=Decimal("100"),
                transaction_id="TX40",
            ),
            _make_action(
                symbol="TEST", parent_symbol="TEST", quantity=Decimal("200"),
                transaction_id="TX41",
            ),
        ]

        result = parser.group_split_actions(actions)
        assert len(result) == 1
        assert result[0].quantity == Decimal("300")
