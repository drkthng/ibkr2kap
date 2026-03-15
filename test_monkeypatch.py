import ibflex.Types
from dataclasses import make_dataclass, field
from typing import Optional

# Monkeypatch CashTransaction to include actionID if missing
if "actionID" not in ibflex.Types.CashTransaction.__annotations__:
    # Create a new dataclass with the extra field
    original_fields = list(ibflex.Types.CashTransaction.__dataclass_fields__.values())
    # ibflex uses specific types, we can use str | None for actionID
    
    # We can't easily replace the class globally if other things reference it,
    # but we can try to add it to __annotations__ and __dataclass_fields__
    ibflex.Types.CashTransaction.__annotations__["actionID"] = Optional[str]
    # This might not be enough for the parser which uses annotations to find attributes
    print("Monkeypatched actionID into ibflex.Types.CashTransaction annotations")
