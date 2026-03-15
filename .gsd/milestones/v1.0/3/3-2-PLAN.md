---
phase: 3
plan: 2
wave: 2
depends_on: [3.1]
files_modified:
  - src/ibkr_tax/services/ecb_rates.py
  - tests/test_ecb_rates.py
autonomous: true
user_setup: []

must_haves:
  truths:
    - "get_rate() returns a Decimal rate for any date — falling back to previous business day for weekends/holidays"
    - "Rates are looked up from DB cache first, only fetching from ECB when missing"
    - "All tests pass with mocked HTTP responses — no real network calls in tests"
  artifacts:
    - "tests/test_ecb_rates.py covers model, parsing, caching, and weekend fallback"
  key_links:
    - "get_rate() is the public API consumed by downstream phases (FIFO engine, tax categorization)"
---

# Plan 3.2: Rate Lookup Service & Tests

<objective>
Add the public `get_rate()` method to `ECBRateFetcher` that provides the primary interface for the rest of the application. This method handles:
1. DB cache lookup first
2. Weekend/holiday fallback (walk backwards up to 7 days to find the most recent rate)
3. Auto-fetch from ECB if the rate is not cached

Also create comprehensive pytest tests covering the full ECB rates module.

Purpose: This is the single-function API that all downstream phases (FIFO engine, tax categorization) will use to convert amounts to EUR at the official ECB rate.

Output: Completed `ecb_rates.py` with `get_rate()` and full test suite in `tests/test_ecb_rates.py`.
</objective>

<context>
Load for context:
- .gsd/SPEC.md
- src/ibkr_tax/models/database.py (ExchangeRate model — from Plan 3.1)
- src/ibkr_tax/services/ecb_rates.py (ECBRateFetcher — from Plan 3.1)
- tests/conftest.py (test session fixtures)
</context>

<tasks>

<task type="auto">
  <name>Add get_rate() method with weekend fallback</name>
  <files>src/ibkr_tax/services/ecb_rates.py</files>
  <action>
    Add `get_rate()` method to `ECBRateFetcher`:

    ```python
    def get_rate(self, currency: str, date_str: str) -> Decimal:
        """Get the ECB reference rate for `currency` on `date_str` (YYYY-MM-DD).

        1. If currency is EUR, return Decimal("1").
        2. Check DB cache for the exact date.
        3. If not found, walk backwards up to 7 days (weekend/holiday fallback).
        4. If still not found, fetch from ECB API for a 14-day window around the date, cache results, then retry lookup.
        5. If no rate exists after fetch, raise ValueError.
        """
        ...
    ```

    Key implementation details:
    - Return `Decimal("1")` immediately for EUR→EUR.
    - Use `datetime.date.fromisoformat(date_str)` for date arithmetic.
    - Walk backwards: query DB for each day from `date` to `date - 7 days`.
    - On cache miss after walk: call `fetch_rates(currency, date-14d, date)` then retry.
    - Raise `ValueError(f"No ECB rate found for {currency} on or near {date_str}")` if truly not available.

    AVOID: Returning float — must return `Decimal`.
    AVOID: Fetching from ECB on every call — always check DB first.
    AVOID: Walking back more than 7 days — this would cross into the previous week; if no rate exists, the currency/date is likely invalid.
  </action>
  <verify>`uv run pytest tests/test_ecb_rates.py -v -k "test_get_rate"` passes</verify>
  <done>get_rate() returns Decimal, checks DB first, walks back up to 7 days for weekends/holidays, auto-fetches on cache miss.</done>
</task>

<task type="auto">
  <name>Create comprehensive test suite</name>
  <files>tests/test_ecb_rates.py</files>
  <action>
    Create `tests/test_ecb_rates.py` with the following test cases:

    **Model Tests:**
    - `test_exchange_rate_model_creation` — Create and query ExchangeRate rows.
    - `test_exchange_rate_unique_constraint` — Duplicate (date, currency) raises IntegrityError.

    **CSV Parsing Tests (no network):**
    - `test_parse_csv_valid` — Feed a sample ECB CSV string, assert correct Decimal values.
    - `test_parse_csv_empty` — Empty CSV returns empty list.

    **get_rate() Tests (mock HTTP, use real DB):**
    - `test_get_rate_eur_returns_one` — EUR→EUR always returns Decimal("1").
    - `test_get_rate_cached` — Pre-insert a rate into DB, confirm get_rate returns it without HTTP.
    - `test_get_rate_weekend_fallback` — Insert Friday rate, request Saturday date, expect Friday's rate.
    - `test_get_rate_holiday_fallback` — Insert rate for day before a gap, request the gap date.
    - `test_get_rate_fetches_on_miss` — Mock urllib to return a valid CSV, confirm rate is fetched, cached, and returned.
    - `test_get_rate_raises_on_unknown_currency` — No rate available even after fetch → ValueError.

    Use `unittest.mock.patch("urllib.request.urlopen")` for mocking HTTP calls.
    Use the `db_session` fixture from conftest.py for all DB tests.

    AVOID: Real HTTP calls — ALL tests must be offline-capable.
    AVOID: Using floats in test assertions — compare Decimal to Decimal.
  </action>
  <verify>
    `uv run pytest tests/test_ecb_rates.py -v` — all tests pass.
    `uv run pytest --tb=short` — full test suite still green.
  </verify>
  <done>10+ tests covering model CRUD, CSV parsing, cache hits, weekend fallback, auto-fetch, and error handling. All tests pass. No real HTTP calls.</done>
</task>

</tasks>

<verification>
After all tasks, verify:
- [ ] `get_rate("EUR", any_date)` returns `Decimal("1")`
- [ ] `get_rate("USD", "2024-01-06")` (Saturday) falls back to Friday's rate
- [ ] Rates fetched from ECB are persisted in `exchange_rates` table
- [ ] No test makes real HTTP calls
- [ ] Full test suite (`pytest`) passes with zero failures
</verification>

<success_criteria>
- [ ] All tests pass (pytest exit code 0)
- [ ] get_rate() is the single public API for exchange rates
- [ ] Weekend/holiday fallback works correctly
- [ ] DB caching prevents redundant ECB API calls
</success_criteria>
