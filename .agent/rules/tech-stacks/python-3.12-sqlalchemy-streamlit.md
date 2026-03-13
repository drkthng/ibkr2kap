# Agent Rules: Python 3.12 + SQLAlchemy + Streamlit

## 1. Project Structure Conventions
- **Source Code**: All application code lives inside `src/ibkr_tax/`.
- **Database Logic**: `src/ibkr_tax/db/`, `models/`.
- **UI Logic**: `src/ibkr_tax/ui/`.
- **Tests**: Under `tests/` utilizing TDD strictly.

## 2. Build / Compile / Lint Commands
- **Dependency Management**: `poetry` or `uv`.
- **Linting/Formatting**: `ruff` (`ruff check .`, `ruff format .`).
- **UI Execution**: `streamlit run src/ibkr_tax/ui/app.py`.

## 3. Testing Framework
- **Framework**: `pytest`.
- **Execution**: `pytest tests/ -v`.
- **Coverage**: `pytest-cov`.
- **TDD Rule**: Always write failing tests first where applicable. 
- **Database Fixtures**: Must use memory (`sqlite:///:memory:`) for test predictability without lingering states.

## 4. Mandatory Security Settings
- Do not commit sensitive IBKR statement files. Add `*.xml` and `*.csv` files containing personal financial data to `.gitignore`.
- Treat all financial inputs as untrusted and strictly validate via `Pydantic`.

## 5. Common Pitfalls specific to this stack
- **Floating Point Math**: NEVER use `float` for currency items. ALWAYS use `decimal.Decimal` in Python, and `Numeric(precision, scale)` in SQLAlchemy.
- **SQLAlchemy 2.0**: Strictly use the 2.0 style syntax (e.g. `DeclarativeBase`, explicit `Mapped[]` or explicit 2.0 typing if preferring `Column(...)`). Do not drop into legacy query usage.
- **Streamlit Re-renders**: Understand that Streamlit re-runs script top-to-bottom on interaction. Cache database connections using `@st.cache_resource` and use `st.session_state` carefully.
