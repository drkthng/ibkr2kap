import csv
import urllib.request
from datetime import date, timedelta
from decimal import Decimal
from io import StringIO
from sqlalchemy import select
from sqlalchemy.orm import Session
from ibkr_tax.models.database import ExchangeRate

class ECBRateFetcher:
    """Fetches and caches ECB daily reference exchange rates."""

    # ECB API URL for daily rates in CSV format
    # Example: https://data-api.ecb.europa.eu/service/data/EXR/D.USD.EUR.SP00.A?startPeriod=2024-01-01&endPeriod=2024-01-31
    ECB_API_URL = "https://data-api.ecb.europa.eu/service/data/EXR/D.{currency}.EUR.SP00.A"

    def __init__(self, session: Session):
        self.session = session

    def get_rate(self, currency: str, date_str: str) -> Decimal:
        """Get the ECB reference rate for `currency` on `date_str` (YYYY-MM-DD).

        1. If currency is EUR, return Decimal("1").
        2. Check DB cache for the exact date.
        3. If not found, walk backwards up to 7 days (weekend/holiday fallback).
        4. If still not found, fetch from ECB API for a 14-day window around the date, cache results, then retry lookup.
        5. If no rate exists after fetch, raise ValueError.
        """
        curr = currency.upper()
        if curr == "EUR":
            return Decimal("1")

        # 1. & 2. & 3. Try cache with fallback
        target_date = date.fromisoformat(date_str)
        for i in range(8):  # 0 to 7 days back
            check_date = (target_date - timedelta(days=i)).isoformat()
            stmt = select(ExchangeRate.rate_to_eur).where(
                ExchangeRate.rate_date == check_date,
                ExchangeRate.source_currency == curr
            )
            rate = self.session.execute(stmt).scalar()
            if rate is not None:
                return rate

        # 4. Cache miss: Fetch a window around the date
        # Window: [target_date - 10, target_date] to catch previous business days
        start_fetch = (target_date - timedelta(days=10)).isoformat()
        end_fetch = date_str
        self.fetch_rates(curr, start_fetch, end_fetch)

        # 5. Retry lookup after fetch
        for i in range(8):
            check_date = (target_date - timedelta(days=i)).isoformat()
            stmt = select(ExchangeRate.rate_to_eur).where(
                ExchangeRate.rate_date == check_date,
                ExchangeRate.source_currency == curr
            )
            rate = self.session.execute(stmt).scalar()
            if rate is not None:
                return rate

        raise ValueError(f"No ECB rate found for {curr} on or near {date_str}")

    def fetch_rates(self, currency: str, start_date: str, end_date: str) -> list[ExchangeRate]:
        """Fetch ECB rates for `currency` in the given date range.
        Returns a list of ExchangeRate objects persisted to DB.
        Skips dates already in the database (idempotent).
        """
        if currency.upper() == "EUR":
            return []

        csv_text = self._fetch_csv_from_ecb(currency.upper(), start_date, end_date)
        rate_dicts = self._parse_csv(csv_text, currency.upper())

        new_rates = []
        for rd in rate_dicts:
            # Idempotency check: skip if date/currency already exists
            stmt = select(ExchangeRate).where(
                ExchangeRate.rate_date == rd["rate_date"],
                ExchangeRate.source_currency == rd["source_currency"]
            )
            existing = self.session.execute(stmt).scalars().first()
            if not existing:
                rate_obj = ExchangeRate(
                    rate_date=rd["rate_date"],
                    source_currency=rd["source_currency"],
                    rate_to_eur=rd["rate_to_eur"]
                )
                self.session.add(rate_obj)
                new_rates.append(rate_obj)
        
        self.session.commit()
        return new_rates

    def _fetch_csv_from_ecb(self, currency: str, start_date: str, end_date: str) -> str:
        """HTTP GET to ECB API, returns raw CSV text."""
        url = f"{self.ECB_API_URL.format(currency=currency)}?startPeriod={start_date}&endPeriod={end_date}"
        headers = {"Accept": "text/csv"}
        req = urllib.request.Request(url, headers=headers)
        
        try:
            with urllib.request.urlopen(req) as response:
                return response.read().decode('utf-8')
        except Exception as e:
            # In a real app, we might want more specific error handling here
            raise ValueError(f"Failed to fetch ECB rates for {currency}: {e}")

    def _parse_csv(self, csv_text: str, currency: str) -> list[dict]:
        """Parse the ECB CSV response.
        Expected format (Standard ECB CSV):
        KEY,FREQ,CURRENCY,CURRENCY_DENOM,EXR_TYPE,EXR_SUFFIX,TIME_PERIOD,OBS_VALUE,...
        Only interested in TIME_PERIOD and OBS_VALUE.
        """
        if not csv_text.strip():
            return []

        f = StringIO(csv_text)
        reader = csv.DictReader(f)
        
        results = []
        for row in reader:
            # ECB CSV headers: TIME_PERIOD, OBS_VALUE
            date_str = row.get("TIME_PERIOD")
            rate_str = row.get("OBS_VALUE")
            
            if date_str and rate_str:
                try:
                    results.append({
                        "rate_date": date_str,
                        "source_currency": currency,
                        "rate_to_eur": Decimal(rate_str)
                    })
                except Exception:
                    # Skip rows with invalid data
                    continue
                    
        return results
