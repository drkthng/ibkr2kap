from typing import Dict, Any
from sqlalchemy.orm import Session

from ibkr_tax.services.flex_parser import FlexXMLParser
from ibkr_tax.services.csv_parser import CSVActivityParser
from ibkr_tax.services.option_engine import OptionEngine
from ibkr_tax.db.repository import import_accounts, import_trades, import_cash_transactions


def run_import(file_path: str, session: Session, file_type: str = "xml") -> Dict[str, Any]:
    """
    Orchestrates the import of IBKR data from a file into the database.
    
    Args:
        file_path: Path to the IBKR file (XML or CSV).
        session: SQLAlchemy session for database access.
        file_type: Type of the file, either 'xml' or 'csv'.
        
    Returns:
        A dictionary containing counts of parsed and inserted records.
    """
    if file_type.lower() == "xml":
        parser = FlexXMLParser(xml_path=file_path)
    elif file_type.lower() == "csv":
        parser = CSVActivityParser(csv_path=file_path)
    else:
        raise ValueError(f"Unsupported file type: {file_type}. Use 'xml' or 'csv'.")

    # Parse all data from the file
    parsed_data = parser.parse_all()
    
    accounts = parsed_data["accounts"]
    trades = parsed_data["trades"]
    cash_txs = parsed_data["cash_transactions"]
    option_eae = parsed_data.get("option_eae", [])

    # Process Option Edge Cases (Adjusts transient 'trades' list and closes option lots in DB)
    if option_eae:
        opt_engine = OptionEngine(session)
        opt_engine.apply_option_adjustments(option_eae, trades)

    # Insert into database using repository functions
    # Order matters: Accounts must come first due to foreign key constraints
    accounts_count = import_accounts(session, accounts)
    trades_count = import_trades(session, trades)
    cash_txs_count = import_cash_transactions(session, cash_txs)

    return {
        "status": "success",
        "file_path": file_path,
        "file_type": file_type,
        "counts": {
            "accounts": {
                "parsed": len(accounts),
                "inserted": accounts_count
            },
            "trades": {
                "parsed": len(trades),
                "inserted": trades_count
            },
            "cash_transactions": {
                "parsed": len(cash_txs),
                "inserted": cash_txs_count
            },
            "option_eae": {
                "parsed": len(option_eae)
            }
        }
    }
