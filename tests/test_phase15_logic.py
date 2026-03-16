from unittest.mock import MagicMock, patch
from ibkr_tax.services.flex_parser import FlexXMLParser

@patch("ibkr_tax.services.flex_parser.parser.parse")
def test_flex_parser_unmapped_entities(mock_parse):
    # Mock the ibflex response object
    mock_response = MagicMock()
    mock_response.FlexStatements = []
    mock_parse.return_value = mock_response

    # A mock XML with known tags and one unknown tag
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<FlexQueryResponse queryName="Test" type="Type">
    <FlexStatements>
        <FlexStatement accountId="U1234567" baseCurrency="EUR">
            <Trades>
                <Trade symbol="AAPL" />
            </Trades>
            <UnknownEntityGroup>
                <UnknownChild field="value" />
            </UnknownEntityGroup>
            <SingleUnknownChild attr="val" />
        </FlexStatement>
    </FlexStatements>
</FlexQueryResponse>
"""
    
    parser = FlexXMLParser(xml_content=xml_content)
    # Check if our new detection logic picked up the unknown tags via ElementTree
    warnings = parser.get_unmapped_entities()
    
    print(f"Warnings found: {warnings}")
    
    # Check for detected unknown tags
    warning_entities = [w['entity'] for w in warnings]
    assert 'UnknownEntityGroup' in warning_entities
    assert 'SingleUnknownChild' in warning_entities
    assert 'Trades' not in warning_entities # Supported
    assert all(w['account_id'] == 'U1234567' for w in warnings)
