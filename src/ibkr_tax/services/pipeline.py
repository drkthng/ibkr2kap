from typing import Dict, Any
from sqlalchemy.orm import Session

from ibkr_tax.services.flex_parser import FlexXMLParser
from ibkr_tax.services.csv_parser import CSVActivityParser
from ibkr_tax.services.option_engine import OptionEngine
from ibkr_tax.db.repository import (
    import_accounts, 
    import_trades, 
    import_cash_transactions,
    import_corporate_actions
)


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
    corporate_actions = parsed_data.get("corporate_actions", [])

    # 1. Insert into database using repository functions
    import_accounts(session, accounts)
    import_trades(session, trades)
    import_cash_transactions(session, cash_txs)
    import_corporate_actions(session, corporate_actions)
    
    # 2. Re-run engines to handle adjustments
    from ibkr_tax.services.fifo_runner import FIFORunner
    fifo_runner = FIFORunner(session)
    
    if option_eae:
        # Initial FIFO run to create lots needed by OptionEngine
        fifo_runner.run_all()
        
        # Process Option Edge Cases (Adjusts DB Trade records and closes option lots in DB)
        opt_engine = OptionEngine(session)
        opt_engine.apply_option_adjustments(option_eae)
        
        # Final FIFO run to account for adjusted trades
        fifo_runner.run_all()
    else:
        # Standard run if no options
        fifo_runner.run_all()

    # 3. Process FX FIFO for Section 23 EStG (§ 23 EStG)
    from ibkr_tax.services.fx_fifo_engine import FXFIFOEngine
    from ibkr_tax.models.database import Account
    from sqlalchemy import select
    fx_engine = FXFIFOEngine(session)
    # We process for all accounts to be safe, as cash transfers can be between accounts
    accounts_in_db = session.execute(select(Account)).scalars().all()
    for acc in accounts_in_db:
        fx_engine.process_all_fx(acc.id)
    session.commit()

    return {
        "status": "success",
        "file_path": file_path,
        "file_type": file_type,
        "counts": {
            "accounts": {"parsed": len(accounts)},
            "trades": {"parsed": len(trades)},
            "cash_transactions": {"parsed": len(cash_txs)},
            "option_eae": {"parsed": len(option_eae)}
        }
    }
