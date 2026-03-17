import pytest
from decimal import Decimal
from datetime import date
from ibkr_tax.services.flex_parser import FlexXMLParser

def test_parse_corporate_actions_spinoff():
    xml_content = """
<FlexQueryResponse>
    <FlexStatements>
        <FlexStatement accountId="U7230673" baseCurrency="CAD">
            <CorporateActions>
                <CorporateAction accountId="U7230673" currency="CAD" symbol="LMN" 
                    description="CSU(CA21037X1006) SPINOFF  3000383 FOR 1000000 (LMN, LUMINE GROUP INC, CA55027C1068)" 
                    isin="CA55027C1068" reportDate="20230215" dateTime="20230214;202500" value="0" 
                    quantity="3.0004" type="SO" transactionID="1673457852" />
            </CorporateActions>
        </FlexStatement>
    </FlexStatements>
</FlexQueryResponse>
"""
    parser = FlexXMLParser(xml_content=xml_content)
    actions = parser.get_corporate_actions()
    
    assert len(actions) == 1
    a = actions[0]
    assert a.symbol == "LMN"
    assert a.parent_symbol == "CSU"
    assert a.action_type == "SO"
    assert a.quantity == Decimal("3.0004")
    assert a.transaction_id == "1673457852"
    assert a.date == date(2023, 2, 14)
    assert a.report_date == date(2023, 2, 15)
    assert a.tax_treatment == "PENDING_REVIEW"

def test_regex_parent_symbol_extraction():
    # Test cases for parent symbol extraction
    from ibkr_tax.services.flex_parser import FlexXMLParser
    parser = FlexXMLParser(xml_content="<FlexQueryResponse><FlexStatements><FlexStatement accountId='U1' /></FlexStatements></FlexQueryResponse>")
    
    # CSU(CA21037X1006) SPINOFF
    assert parser._extract_parent_symbol("CSU(CA21037X1006) SPINOFF") == "CSU"
    # VNA(DE000A1ML7J1) DIVIDEND RIGHTS ISSUE
    assert parser._extract_parent_symbol("VNA(DE000A1ML7J1) DIVIDEND") == "VNA"
    # DEC(GB00BYX7JT74) SPLIT
    assert parser._extract_parent_symbol("DEC(GB00BYX7JT74) SPLIT") == "DEC"
    # No match
    assert parser._extract_parent_symbol("JUST SOME TEXT") is None
