from ibkr_tax.services.flex_parser import FlexXMLParser
import os
from decimal import Decimal

xml_path = r"d:\Antigravity\IBKR2KAP\example\U7230673_20240101_20241231_AF_1434039_b9efd8fc4d9a876b70112f66fdb53969.xml"

parser = FlexXMLParser(xml_path=xml_path)
statement = parser.response.FlexStatements[0]

if statement.CashTransactions:
    ct = next(tx for tx in statement.CashTransactions if str(tx.amount) == "-0.2")
    print(f"CT dateTime: {ct.dateTime} (Type: {type(ct.dateTime)})")
    print(f"CT type: {ct.type} (Value: {ct.type.value})")
    print(f"CT amount: {ct.amount}")
    
    # Check what keys are in action_ids
    print(f"Action IDs keys count: {len(parser.action_ids)}")
    first_key = list(parser.action_ids.keys())[0] if parser.action_ids else None
    print(f"Sample key from action_ids: {first_key}")
    
    # Compute the key we're using in get_cash_transactions
    account_id = getattr(statement, "accountId", "UNKNOWN")
    lookup_key = (account_id, str(ct.dateTime), str(ct.amount), str(ct.type.value))
    print(f"Lookup key: {lookup_key}")
    print(f"Key in action_ids? {lookup_key in parser.action_ids}")
