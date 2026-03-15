import ibflex
from ibflex import parser
import os
from decimal import Decimal

xml_path = r"d:\Antigravity\IBKR2KAP\example\U7230673_20240101_20241231_AF_1434039_b9efd8fc4d9a876b70112f66fdb53969.xml"

try:
    response = parser.parse(xml_path)
    statement = response.FlexStatements[0]
    print(f"Statement attributes: {[a for a in dir(statement) if not a.startswith('_')]}")
    
    if statement.Trades:
        trade = statement.Trades[0]
        print(f"Trade attributes: {[a for a in dir(trade) if not a.startswith('_')]}")
        print(f"Trade symbol: {trade.symbol}")
    
    if statement.CashTransactions:
        ct = statement.CashTransactions[0]
        print(f"CashTransaction attributes: {[a for a in dir(ct) if not a.startswith('_')]}")
        print(f"CT Type: {ct.type}")
        # Let's see what attributes it DOES have for action/ID
        print(f"CT attributes for ID: {[a for a in dir(ct) if 'ID' in a]}")
except Exception as e:
    import traceback
    traceback.print_exc()
