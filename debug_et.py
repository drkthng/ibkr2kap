import xml.etree.ElementTree as ET
from decimal import Decimal
from datetime import datetime

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

root = ET.fromstring(xml_content)
print("Root tag:", root.tag)
found = root.findall(".//CorporateAction")
print("Found count:", len(found))

for ca_elem in found:
    print("Action type:", ca_elem.get("type"))
    dt_str = ca_elem.get("dateTime", "")
    print("DateTime str:", dt_str)
    action_date = datetime.strptime(dt_str.split(";")[0], "%Y%m%d").date()
    print("Action date:", action_date)
