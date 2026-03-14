---
phase: 3
plan: 1
wave: 1
depends_on: []
files_modified:
  - src/ibkr_tax/models/database.py
  - src/ibkr_tax/services/__init__.py
  - src/ibkr_tax/services/ecb_rates.py
  - tests/test_ecb_rates.py
autonomous: true
user_setup: []

must_haves:
  truths:
    - "ExchangeRate model stores date, source_currency, rate_to_eur as Decimal"
    - "ECB CSV daily rates can be fetched and parsed into Decimal values"
    - "Parsed rates are persisted to the exchange_rates table"
  artifacts:
    - "src/ibkr_tax/models/database.py contains ExchangeRate model"
    - "src/ibkr_tax/services/ecb_rates.py contains ECBRateFetcher class"
  key_links:
    - "ExchangeRate model uses Numeric(18,6) — same precision as fx_rate_to_base in Trade/CashTransaction"
---

# Plan 3.1: ExchangeRate Model & ECB Fetcher

<objective>
Create the database model for caching exchange rates and a service that fetches official ECB daily reference rates from the ECB API, parsing them into `Decimal` values and persisting them to the database.

Purpose: The tax engine needs official ECB rates (not IBKR-provided ones) for converting foreign-currency transactions to EUR. Rates must be cached in the DB so we only fetch once per currency/date range.

Output: `ExchangeRate` model, `ECBRateFetcher` service class, and unit tests.
</objective>

<context>
Load for context:
- .gsd/SPEC.md
- src/ibkr_tax/models/database.py (existing models, Base class, Numeric conventions)
- src/ibkr_tax/db/engine.py (DB engine setup)
- tests/conftest.py (test session fixtures)
</context>

<tasks>

<task type="auto">
  <name>Add ExchangeRate model to database.py</name>
  <files>src/ibkr_tax/models/database.py</files>
  <action>
    Add a new `ExchangeRate` SQLAlchemy model to the existing `database.py`:

    ```python
    class ExchangeRate(Base):
        __tablename__ = "exchange_rates"
        __table_args__ = (
            UniqueConstraint("rate_date", "source_currency", name="uq_rate_date_currency"),
        )

        id: Mapped[int] = mapped_column(primary_key=True)
        rate_date: Mapped[str] = mapped_column(index=True)  # ISO date string YYYY-MM-DD
        source_currency: Mapped[str] = mapped_column()       # e.g. "USD", "GBP"
        rate_to_eur: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    ```

    Import `UniqueConstraint` from `sqlalchemy` at the top of the file.

    AVOID: Using `float` for the rate — must be `Numeric(18, 6)` with `Decimal` mapped type.
    AVOID: Using `Date` type — keep consistent with existing models that use ISO string dates.
  </action>
  <verify>
    `uv run pytest tests/test_db_setup.py -v` — existing DB tests still pass (table creation).
    Verify the new model is included in Base.metadata.tables.
  </verify>
  <done>ExchangeRate model exists in database.py with UniqueConstraint on (rate_date, source_currency), uses Numeric(18,6) for rate_to_eur, and existing tests still pass.</done>
</task>

<task type="auto">
  <name>Create ECBRateFetcher service</name>
  <files>
    src/ibkr_tax/services/__init__.py
    src/ibkr_tax/services/ecb_rates.py
  </files>
  <action>
    Create `src/ibkr_tax/services/` package with `__init__.py`.

    Create `ecb_rates.py` containing an `ECBRateFetcher` class:

    ```python
    class ECBRateFetcher:
        """Fetches and caches ECB daily reference exchange rates."""

        ECB_API_URL = "https://data-api.ecb.europa.eu/service/data/EXR/D.{currency}.EUR.SP00.A"

        def __init__(self, session: Session):
            self.session = session

        def fetch_rates(
            self, currency: str, start_date: str, end_date: str
        ) -> list[ExchangeRate]:
            """Fetch ECB rates for `currency` in the given date range.
            Returns a list of ExchangeRate objects persisted to DB.
            Skips dates already in the database (idempotent).
            """
            ...

        def _fetch_csv_from_ecb(
            self, currency: str, start_date: str, end_date: str
        ) -> str:
            """HTTP GET to ECB API, returns raw CSV text."""
            ...

        def _parse_csv(self, csv_text: str, currency: str) -> list[dict]:
            """Parse the ECB CSV response into a list of
            {"rate_date": "YYYY-MM-DD", "source_currency": "USD", "rate_to_eur": Decimal("1.0834")}
            dicts. Uses `csv` stdlib module — NOT pandas.
            Converts all rates to Decimal immediately.
            """
            ...
    ```

    Use `urllib.request` (stdlib) for the HTTP call — avoid adding `requests` as a new dependency.
    Set the `Accept: text/csv` header on the request.
    The ECB API URL pattern: `https://data-api.ecb.europa.eu/service/data/EXR/D.{currency}.EUR.SP00.A?startPeriod={start}&endPeriod={end}`

    AVOID: Using `float()` anywhere — parse rates directly to `Decimal(rate_string)`.
    AVOID: Using pandas for CSV parsing — this is a simple 2-column CSV; use `csv.DictReader`.
    AVOID: Adding `requests` to dependencies — use `urllib.request` from stdlib.
  </action>
  <verify>
    `uv run pytest tests/test_ecb_rates.py -v` — new tests pass (see task in Plan 3.2).
  </verify>
  <done>ECBRateFetcher class exists, fetches ECB CSV, parses to Decimal, persists ExchangeRate rows idempotently, uses only stdlib for HTTP.</done>
</task>

</tasks>

<verification>
After all tasks, verify:
- [ ] `ExchangeRate` model has UniqueConstraint on (rate_date, source_currency)
- [ ] `rate_to_eur` is `Numeric(18, 6)` mapping to `Decimal`
- [ ] ECBRateFetcher uses stdlib `urllib.request`, not `requests`
- [ ] CSV parsing converts directly to `Decimal` — no floats
- [ ] Existing tests (`test_db_setup.py`, `test_schemas.py`) still pass
</verification>

<success_criteria>
- [ ] All existing tests pass
- [ ] ExchangeRate model creates correctly in SQLite
- [ ] ECBRateFetcher can parse a known ECB CSV response
</success_criteria>
