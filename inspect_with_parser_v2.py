from ibkr_tax.services.flex_parser import FlexXMLParser
import os

xml_path = r"d:\Antigravity\IBKR2KAP\example\U7230673_20240101_20241231_AF_1434039_b9efd8fc4d9a876b70112f66fdb53969.xml"

parser = FlexXMLParser(xml_path=xml_path)
statement = parser.response.FlexStatements[0]

print(f"Statement accountId: {getattr(statement, 'accountId', 'MISSING')}")

# Try to find currency
if hasattr(statement, "AccountInformation") and statement.AccountInformation:
    acc_info = statement.AccountInformation[0]
    print(f"AccountInfo attributes: {[a for a in dir(acc_info) if not a.startswith('_')]}")
    print(f"AccountInfo currency: {getattr(acc_info, 'currency', 'MISSING')}")
else:
    print("AccountInformation is MISSING or NONE")

# Check Trade Enum values
if statement.Trades:
    trade = statement.Trades[0]
    print(f"Trade assetCategory: {trade.assetCategory} (Value: {trade.assetCategory.value if hasattr(trade.assetCategory, 'value') else 'N/A'})")
    print(f"Trade buySell: {trade.buySell} (Value: {trade.buySell.value if hasattr(trade.buySell, 'value') else 'N/A'})")

# Check CashTransaction Enum value
if statement.CashTransactions:
    ct = statement.CashTransactions[0]
    print(f"CT type: {ct.type} (Value: {ct.type.value if hasattr(ct.type, 'value') else 'N/A'})")
