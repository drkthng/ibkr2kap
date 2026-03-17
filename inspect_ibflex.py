import ibflex
import ibflex.Types as T
from ibflex import parser

print("ibflex version:", getattr(ibflex, "__version__", "unknown"))
print("Types in T:")
for name in sorted(dir(T)):
    if not name.startswith("__"):
        print(f"  {name}")

xml = """<FlexQueryResponse><FlexStatements><FlexStatement accountId="U1"><Trades /></FlexStatement></FlexStatements></FlexQueryResponse>"""
try:
    print("\nAttempting to parse minimal XML...")
    response = parser.parse(xml.encode("utf-8"))
    print("Response type:", type(response))
    print("Response attributes:", [a for a in dir(response) if not a.startswith("_")])
except Exception as e:
    print("Error during parse:", e)
    import traceback
    traceback.print_exc()
