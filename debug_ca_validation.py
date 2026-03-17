from ibkr_tax.services.flex_parser import FlexXMLParser
from ibkr_tax.schemas.ibkr import CorporateActionSchema
from ibkr_tax.models.database import CorporateAction
import traceback
from decimal import Decimal

# Mock a DB object
class MockDBObj:
    id = 1
    account_id = 100 # internal ID
    symbol = "LMN"
    parent_symbol = "CSU"
    action_type = "SO"
    date = "2023-02-14"
    report_date = "2023-02-15"
    quantity = Decimal("3.0004")
    value = Decimal("0")
    isin = "CA55027C1068"
    currency = "CAD"
    transaction_id = "1673457852"
    description = "CSU SPINOFF"
    tax_treatment = "PENDING_REVIEW"

print("Attempting to validate mock DB object...")
try:
    schema = CorporateActionSchema.model_validate(MockDBObj())
    print("Successfully validated!")
except Exception as e:
    print(f"Validation error: {e}")
    if hasattr(e, "errors"):
        import json
        print(json.dumps(e.errors(), indent=2))
