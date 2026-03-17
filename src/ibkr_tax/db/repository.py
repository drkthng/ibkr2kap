from sqlalchemy import select, func, distinct
from sqlalchemy.orm import Session
from sqlalchemy.dialects.sqlite import insert

from ibkr_tax.models.database import Account, Trade, CashTransaction, CorporateAction, Transfer, Gain
from ibkr_tax.schemas.ibkr import AccountSchema, TradeSchema, CashTransactionSchema, CorporateActionSchema, TransferSchema


def import_accounts(session: Session, accounts: list[AccountSchema]) -> int:
    """Inserts accounts into the DB. Ignores duplicates based on account_id."""
    if not accounts:
        return 0

    stmt = insert(Account).values([acc.to_db_dict() for acc in accounts])
    stmt = stmt.on_conflict_do_nothing(index_elements=['account_id'])
    
    result = session.execute(stmt)
    session.commit()
    return result.rowcount


def import_trades(session: Session, trades: list[TradeSchema]) -> int:
    """Inserts trades into the DB. Ignores duplicates based on ib_trade_id."""
    if not trades:
        return 0

    # Get a map from IBKR string account_id to internal integer Account.id
    account_map = {acc.account_id: acc.id for acc in session.query(Account).all()}
    
    values = []
    for trade in trades:
        trade_dict = trade.to_db_dict()
        if trade.account_id not in account_map:
            raise ValueError(f"Account {trade.account_id} not found in database. Import accounts first.")
        trade_dict['account_id'] = account_map[trade.account_id]
        values.append(trade_dict)

    stmt = insert(Trade).values(values)
    stmt = stmt.on_conflict_do_nothing(index_elements=['ib_trade_id'])
    
    result = session.execute(stmt)
    session.commit()
    return result.rowcount


def import_cash_transactions(session: Session, cash_txs: list[CashTransactionSchema]) -> int:
    """Inserts cash transactions into the DB avoiding duplicates by doing a pre-flight query."""
    if not cash_txs:
        return 0

    account_map = {acc.account_id: acc.id for acc in session.query(Account).all()}
    
    inserted = 0
    for cx in cash_txs:
        if cx.account_id not in account_map:
            raise ValueError(f"Account {cx.account_id} not found in database. Import accounts first.")
            
        internal_acc_id = account_map[cx.account_id]
        cx_dict = cx.to_db_dict()
        cx_dict['account_id'] = internal_acc_id
        
        # Pre-flight query to find if transaction already exists
        query = session.query(CashTransaction).filter_by(
            account_id=internal_acc_id,
            date_time=cx_dict['date_time'],
            amount=cx_dict['amount'],
            type=cx_dict['type']
        )
        
        if cx_dict.get('action_id'):
            query = query.filter_by(action_id=cx_dict['action_id'])
        else:
            query = query.filter_by(description=cx_dict['description'])
            
        existing = query.first()
        if not existing:
            new_tx = CashTransaction(**cx_dict)
            session.add(new_tx)
            inserted += 1
            
    session.commit()
    return inserted


def import_corporate_actions(session: Session, actions: list[CorporateActionSchema]) -> int:
    """Inserts corporate actions into the DB."""
    if not actions:
        return 0

    account_map = {acc.account_id: acc.id for acc in session.query(Account).all()}
    
    inserted = 0
    for action in actions:
        if action.account_id not in account_map:
             raise ValueError(f"Account {action.account_id} not found. Import accounts first.")
             
        internal_acc_id = account_map[action.account_id]
        ca_dict = action.to_db_dict()
        ca_dict['account_id'] = internal_acc_id
        
        # Avoid exact duplicates using transaction_id
        existing = session.query(CorporateAction).filter_by(
            account_id=internal_acc_id,
            transaction_id=ca_dict['transaction_id']
        ).first()
        
        if not existing:
            new_ca = CorporateAction(**ca_dict)
            session.add(new_ca)
            inserted += 1
            
    session.commit()
    return inserted


def import_transfers(session: Session, transfers: list[TransferSchema]) -> int:
    """Inserts transfers into the DB. Avoids duplicates via UniqueConstraint fields."""
    if not transfers:
        return 0

    account_map = {acc.account_id: acc.id for acc in session.query(Account).all()}

    inserted = 0
    for transfer in transfers:
        if transfer.account_id not in account_map:
            # Skip transfers for accounts not in DB (e.g., counterparty not imported)
            continue

        internal_acc_id = account_map[transfer.account_id]
        t_dict = transfer.to_db_dict()
        t_dict['account_id'] = internal_acc_id

        # Check for existing transfer using the unique constraint fields
        existing = session.query(Transfer).filter_by(
            account_id=internal_acc_id,
            symbol=t_dict['symbol'],
            transfer_date=t_dict['transfer_date'],
            direction=t_dict['direction'],
            quantity=t_dict['quantity'],
        ).first()

        if not existing:
            new_transfer = Transfer(**t_dict)
            session.add(new_transfer)
            inserted += 1

    session.commit()
    return inserted


def get_distinct_account_ids(session: Session) -> list[str]:
    """Returns a sorted list of unique IBKR account IDs (string) in the DB."""
    stmt = select(Account.account_id).order_by(Account.account_id)
    results = session.execute(stmt).scalars().all()
    return list(results)


def get_tax_years_for_account(session: Session, account_identifier: str) -> list[int]:
    """
    Returns a sorted list of tax years (int, descending) that have data for the account.
    Checks both the Gain table (realized trades) and CashTransaction table (dividends/interest).
    """
    # 1. Resolve internal account ID
    stmt_acc = select(Account.id).where(Account.account_id == account_identifier)
    account_db_id = session.execute(stmt_acc).scalar()

    if account_db_id is None:
        return []

    # 2. Get years from Gains
    stmt_gain_years = (
        select(distinct(Gain.tax_year))
        .join(Trade, Gain.sell_trade_id == Trade.id)
        .where(Trade.account_id == account_db_id)
    )
    gain_years = set(session.execute(stmt_gain_years).scalars().all())

    # 3. Get years from CashTransactions (using substr of settle_date YYYY-MM-DD)
    stmt_cash_years = (
        select(distinct(func.substr(CashTransaction.settle_date, 1, 4)))
        .where(CashTransaction.account_id == account_db_id)
    )
    cash_years_raw = session.execute(stmt_cash_years).scalars().all()
    cash_years = {int(y) for y in cash_years_raw if y}

    # 4. Merge and sort
    all_years = sorted(gain_years.union(cash_years), reverse=True)
    return all_years
