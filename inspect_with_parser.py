from ibkr_tax.services.flex_parser import FlexXMLParser
import os

xml_path = r"d:\Antigravity\IBKR2KAP\example\U7230673_20240101_20241231_AF_1434039_b9efd8fc4d9a876b70112f66fdb53969.xml"

parser = FlexXMLParser(xml_path=xml_path)
statement = parser.response.FlexStatements[0]
print(f"FlexStatement attributes: {[a for a in dir(statement) if not a.startswith('_')]}")

if statement.Trades:
    trade = statement.Trades[0]
    print(f"Trade attributes: {[a for a in dir(trade) if not a.startswith('_')]}")
    print(f"Trade assetCategory type: {type(trade.assetCategory)}")
    print(f"Trade buySell type: {type(trade.buySell)}")

if statement.CashTransactions:
    ct = statement.CashTransactions[0]
    print(f"CashTransaction attributes: {[a for a in dir(ct) if not a.startswith('_')]}")
    print(f"CT type type: {type(ct.type)}")
