---
phase: 0
plan: 2
wave: 1
---

# Plan 0.2: Database Models and Initial Test

## Objective
Implement the database models for Phase 0 to ensure basic SQLite scaffolding works and we can execute a "Hello World" test for the DB setup.

## Context
- .gsd/SPEC.md
- .gsd/ROADMAP.md
- .agent/rules/tech-stacks/python-3.12-sqlalchemy-streamlit.md

## Tasks

<task type="auto">
  <name>Database Models Setup</name>
  <files>
    - `d:/Antigravity/IBKR2KAP/src/ibkr_tax/models/__init__.py`
    - `d:/Antigravity/IBKR2KAP/src/ibkr_tax/models/database.py`
  </files>
  <action>
    - Create `src/ibkr_tax/models/database.py`.
    - Set up the explicit `DeclarativeBase` for SQLAlchemy 2.0.
    - Create a simple dummy model (e.g. `Account` with an `id` and `account_id`) just to prove the DB creation works.
  </action>
  <verify>uv run python -c "from ibkr_tax.models.database import Base; print('Models OK')" → Models OK</verify>
  <done>Models module is created and imports cleanly.</done>
</task>

<task type="auto">
  <name>Hello World Test Setup</name>
  <files>
    - `d:/Antigravity/IBKR2KAP/tests/conftest.py`
    - `d:/Antigravity/IBKR2KAP/tests/test_db_setup.py`
  </files>
  <action>
    - Create `tests/conftest.py` with `db_engine` (using `sqlite:///:memory:`) and `db_session` fixtures.
    - Create `tests/test_db_setup.py` that asserts that `init_db` from `src.ibkr_tax.db.engine` runs without raising exceptions and that the `Account` table is created.
  </action>
  <verify>uv run pytest tests/test_db_setup.py -v → 1 passed</verify>
  <done>Pytest discovers the test and passes the basic DB scaffolding check.</done>
</task>

## Success Criteria
- [ ] Pytest runs successfully.
- [ ] The SQLite in-memory database initializes without error.
