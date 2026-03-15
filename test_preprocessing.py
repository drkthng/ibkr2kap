import ibflex
from ibflex import parser
import re

xml_path = r"d:\Antigravity\IBKR2KAP\example\U7230673_20240101_20241231_AF_1434039_b9efd8fc4d9a876b70112f66fdb53969.xml"

def parse_with_preprocessing(path):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Strip actionID="...", isin="..." and other potentially unknown fields from CashTransaction
    # ibflex 0.15 seems to have issues with actionID and isin in CashTransaction
    clean_content = re.sub(r'(<CashTransaction[^>]+)\bactionID="[^"]*"', r'\1', content)
    clean_content = re.sub(r'(<CashTransaction[^>]+)\bisin="[^"]*"', r'\1', clean_content)
    
    return parser.parse(clean_content.encode("utf-8"))

try:
    response = parse_with_preprocessing(xml_path)
    print(f"Successfully parsed with preprocessing! Trades: {len(response.FlexStatements[0].Trades)}")
    print(f"CashTransactions: {len(response.FlexStatements[0].CashTransactions)}")
except Exception as e:
    import traceback
    traceback.print_exc()
