---
phase: 0
plan: 1
wave: 1
---

# Plan 0.1: Scaffolding and Dependencies

## Objective
Set up the core project layout and base dependencies using `uv` as preferred by the user, and establish the main SQLite database shell.

## Context
- .gsd/SPEC.md
- .gsd/ROADMAP.md
- .agent/rules/tech-stacks/python-3.12-sqlalchemy-streamlit.md
- src/ibkr_tax/

## Tasks

<task type="auto">
  <name>Initialize Project Structure</name>
  <files>
    - `d:/Antigravity/IBKR2KAP/pyproject.toml`
    - `d:/Antigravity/IBKR2KAP/src/ibkr_tax/__init__.py`
    - `d:/Antigravity/IBKR2KAP/tests/__init__.py`
  </files>
  <action>
    - Initialize a new Python project using `uv init` in the root directory.
    - Set the python version constraint to `>=3.12` in `pyproject.toml`.
    - Install base dependencies via `uv add`: `sqlalchemy`, `alembic`, `pydantic`, `pandas`, `pytest`, `pytest-cov`, `ruff`, `ibflex`, `CurrencyConverter`, `openpyxl`, `streamlit`.
    - Create the standard package structure `src/ibkr_tax/` and a `tests/` directory with empty `__init__.py` files to make them modules.
  </action>
  <verify>uv run python -c "import sqlalchemy; import pydantic; import streamlit; print('OK')" → OK</verify>
  <done>Project layout is created, `pyproject.toml` is populated with the correct dependencies, and `uv` has successfully installed them.</done>
</task>

<task type="auto">
  <name>Database Engine and Session Setup</name>
  <files>
    - `d:/Antigravity/IBKR2KAP/src/ibkr_tax/db/__init__.py`
    - `d:/Antigravity/IBKR2KAP/src/ibkr_tax/db/engine.py`
  </files>
  <action>
    - Create `src/ibkr_tax/db/engine.py`.
    - Import `create_engine` and `sessionmaker` from `sqlalchemy`.
    - Define a `get_engine(db_url: str = "sqlite:///ibkr_tax.db")` function that returns a SQLAlchemy engine.
    - Define a `get_session(engine)` function returning a configured `Session` class.
    - Define an `init_db(engine, base_metadata)` function to create all tables (even if none exist yet).
  </action>
  <verify>uv run python -c "from ibkr_tax.db.engine import get_engine; print(get_engine())" → Engine(sqlite:///ibkr_tax.db)</verify>
  <done>The database engine module is created and can be imported without errors.</done>
</task>

## Success Criteria
- [ ] Requirements from SPEC.md Phase 0 are met.
- [ ] Dependencies are correctly managed by `uv`.
- [ ] Database engine logic exists.
