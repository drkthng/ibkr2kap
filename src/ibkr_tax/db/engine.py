from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.schema import MetaData

def get_engine(db_url: str = "sqlite:///ibkr_tax.db"):
    """Returns a SQLAlchemy engine."""
    return create_engine(db_url, echo=False)

def get_session(engine) -> sessionmaker:
    """Returns a configured Session class."""
    return sessionmaker(bind=engine)

def init_db(engine, base_metadata: MetaData):
    """Creates all tables defined in the metadata."""
    base_metadata.create_all(engine)

def migrate_schema(engine, base_metadata: MetaData):
    """Auto-migrate: create missing tables, add missing columns, drop stale columns,
    and recreate tables whose column constraints have changed.

    Handles:
      1. Entirely missing tables  -> CREATE TABLE via create_all()
      2. Missing columns          -> ALTER TABLE ADD COLUMN
      3. Stale columns            -> ALTER TABLE DROP COLUMN  (SQLite >= 3.35)
      4. Constraint mismatches    -> Recreate the table (SQLite cannot ALTER constraints)

    Safe to call on every startup — it is idempotent.
    """
    # Step 1: create any entirely missing tables
    base_metadata.create_all(engine)

    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    with engine.begin() as conn:
        for table_name, table in base_metadata.tables.items():
            if table_name not in existing_tables:
                continue  # Already created by create_all above

            db_columns = {col["name"]: col for col in inspector.get_columns(table_name)}
            model_columns = {col.name: col for col in table.columns}

            # --- Step 2: Add columns that exist in model but not in DB ---
            added = False
            for col_name, column in model_columns.items():
                if col_name in db_columns:
                    continue
                added = True

                col_type = column.type.compile(dialect=engine.dialect)

                default_clause = ""
                if not column.nullable and column.default is not None:
                    default_val = column.default.arg
                    if isinstance(default_val, str):
                        default_clause = f" DEFAULT '{default_val}'"
                    elif isinstance(default_val, bool):
                        default_clause = f" DEFAULT {1 if default_val else 0}"
                    elif isinstance(default_val, (int, float)):
                        default_clause = f" DEFAULT {default_val}"
                    else:
                        default_clause = f" DEFAULT '{default_val}'"

                null_clause = "" if column.nullable else " NOT NULL"

                if null_clause and not default_clause:
                    default_clause = " DEFAULT ''"

                stmt = f'ALTER TABLE "{table_name}" ADD COLUMN "{col_name}" {col_type}{null_clause}{default_clause}'
                conn.execute(text(stmt))

            # --- Step 3: Drop columns that exist in DB but not in model ---
            stale = set(db_columns.keys()) - set(model_columns.keys())
            if stale:
                try:
                    for stale_col in stale:
                        conn.execute(text(f'ALTER TABLE "{table_name}" DROP COLUMN "{stale_col}"'))
                except Exception:
                    # DROP COLUMN can fail in SQLite when the column is part of a
                    # foreign key or index.  Fall back to the full table-recreate.
                    _recreate_table(conn, table, engine)
                    continue  # skip step 4 — table was already rebuilt

            # --- Step 4: Check for constraint mismatches (nullability changes) ---
            # If any shared column changed from NOT NULL -> nullable (or vice versa),
            # SQLite requires recreating the table.
            if not added and not stale:
                needs_recreate = False
                shared_cols = set(db_columns.keys()) & set(model_columns.keys())
                for col_name in shared_cols:
                    db_nullable = db_columns[col_name].get("nullable", True)
                    model_nullable = model_columns[col_name].nullable
                    if model_nullable is None:
                        model_nullable = True
                    if db_nullable != model_nullable:
                        needs_recreate = True
                        break

                if needs_recreate:
                    _recreate_table(conn, table, engine)


def _recreate_table(conn, table, engine):
    """Recreate a table to apply constraint changes (the SQLite way).

    1. Rename existing table to _old_<name>
    2. Drop indexes that belonged to the original table (they survive RENAME)
    3. Create fresh table with correct schema (including indexes)
    4. Copy data (only columns that exist in both old and new)
    5. Drop old table
    """
    table_name = table.name
    old_name = f"_old_{table_name}"

    # Get current columns in DB for the data copy
    inspector = inspect(engine)
    db_col_names = [col["name"] for col in inspector.get_columns(table_name)]
    model_col_names = [col.name for col in table.columns]
    # Only copy columns that exist in both old DB and new model
    common_cols = [c for c in model_col_names if c in db_col_names]

    # Collect index names BEFORE renaming (indexes survive rename with their original names)
    idx_names = [idx["name"] for idx in inspector.get_indexes(table_name) if idx["name"]]

    if not common_cols:
        # No overlap — just drop and recreate
        conn.execute(text(f'DROP TABLE "{table_name}"'))
        table.create(bind=engine)
        return

    cols_csv = ", ".join(f'"{c}"' for c in common_cols)

    # Clean up any leftover _old_ table from a previously failed migration
    conn.execute(text(f'DROP TABLE IF EXISTS "{old_name}"'))
    conn.execute(text(f'ALTER TABLE "{table_name}" RENAME TO "{old_name}"'))
    # Drop surviving indexes so table.create() can recreate them cleanly
    for idx_name in idx_names:
        conn.execute(text(f'DROP INDEX IF EXISTS "{idx_name}"'))
    # Create the new table with correct schema
    table.create(bind=engine)
    # Copy data
    conn.execute(text(f'INSERT INTO "{table_name}" ({cols_csv}) SELECT {cols_csv} FROM "{old_name}"'))
    conn.execute(text(f'DROP TABLE "{old_name}"'))
