from ibflex import parser
import xml.etree.ElementTree as ET

with open("example/U7230673_IBKR2KAP_Full_Export_2023.xml", "r", encoding="utf-8") as f:
    xml_data = f.read()

# Try to parse with ET first to see what we have
root = ET.fromstring(xml_data)
print("Root tag:", root.tag)
for child in root:
    print(f"  Child tag: {child.tag}")
    for grandchild in child:
        print(f"    Grandchild tag: {grandchild.tag}")
        break # only one
    break # only one

# Now try parser.parse
try:
    response = parser.parse(xml_data.encode("utf-8"))
    print("ibflex response type:", type(response))
    if hasattr(response, "FlexStatements"):
        print("FlexStatements is present on response")
except Exception as e:
    print("ibflex error:", e)
