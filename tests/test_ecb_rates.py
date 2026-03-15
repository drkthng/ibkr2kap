import pytest
from decimal import Decimal
from unittest.mock import patch, MagicMock
from io import BytesIO
from sqlalchemy import select
from ibkr_tax.models.database import ExchangeRate
from ibkr_tax.services.ecb_rates import ECBRateFetcher

# Sample ECB CSV content
SAMPLE_CSV_2024 = """KEY,FREQ,CURRENCY,CURRENCY_DENOM,EXR_TYPE,EXR_SUFFIX,TIME_PERIOD,OBS_VALUE,OBS_STATUS,OBS_CONF,OBS_PRE_BREAK,OBS_COM,TIME_FORMAT,BREAK,COLLECTION,COMPILATION,COVERAGE,DECIMALS,DOM_SER_ID,EXT_ID,PUBL_ECB,PUBL_MU,PUBL_PUBLIC,TITLE,TITLE_COMPL,UNIT,UNIT_INDEX,UNIT_MULT
EXR.D.USD.EUR.SP00.A,D,USD,EUR,SP00,A,2024-01-05,1.0921,A,F,,,,P1D,,,,,4,,,,,,,,USD,,0
EXR.D.USD.EUR.SP00.A,D,USD,EUR,SP00,A,2024-01-04,1.0945,A,F,,,,P1D,,,,,4,,,,,,,,USD,,0
EXR.D.USD.EUR.SP00.A,D,USD,EUR,SP00,A,2024-01-03,1.0934,A,F,,,,P1D,,,,,4,,,,,,,,USD,,0
"""

SAMPLE_CSV_2023 = """KEY,FREQ,CURRENCY,CURRENCY_DENOM,EXR_TYPE,EXR_SUFFIX,TIME_PERIOD,OBS_VALUE,OBS_STATUS,OBS_CONF,OBS_PRE_BREAK,OBS_COM,TIME_FORMAT,BREAK,COLLECTION,COMPILATION,COVERAGE,DECIMALS,DOM_SER_ID,EXT_ID,PUBL_ECB,PUBL_MU,PUBL_PUBLIC,TITLE,TITLE_COMPL,UNIT,UNIT_INDEX,UNIT_MULT
EXR.D.USD.EUR.SP00.A,D,USD,EUR,SP00,A,2023-01-05,1.0921,A,F,,,,P1D,,,,,4,,,,,,,,USD,,0
EXR.D.USD.EUR.SP00.A,D,USD,EUR,SP00,A,2023-01-04,1.0945,A,F,,,,P1D,,,,,4,,,,,,,,USD,,0
EXR.D.USD.EUR.SP00.A,D,USD,EUR,SP00,A,2023-01-03,1.0934,A,F,,,,P1D,,,,,4,,,,,,,,USD,,0
"""

def test_exchange_rate_model_creation(db_session):
    rate = ExchangeRate(rate_date="1999-01-01", source_currency="USD", rate_to_eur=Decimal("1.1"))
    db_session.add(rate)
    db_session.flush()
    
    stmt = select(ExchangeRate).where(ExchangeRate.rate_date == "1999-01-01")
    fetched = db_session.execute(stmt).scalar()
    assert fetched.rate_to_eur == Decimal("1.1")

def test_parse_csv_valid():
    fetcher = ECBRateFetcher(None)
    results = fetcher._parse_csv(SAMPLE_CSV_2024, "USD")
    assert len(results) == 3
    assert results[0]["rate_date"] == "2024-01-05"
    assert results[0]["rate_to_eur"] == Decimal("1.0921")
    assert results[2]["rate_date"] == "2024-01-03"
    assert results[2]["rate_to_eur"] == Decimal("1.0934")

def test_parse_csv_empty():
    fetcher = ECBRateFetcher(None)
    assert fetcher._parse_csv("", "USD") == []
    assert fetcher._parse_csv("   \n ", "USD") == []

def test_get_rate_eur_returns_one(db_session):
    fetcher = ECBRateFetcher(db_session)
    assert fetcher.get_rate("EUR", "2024-01-01") == Decimal("1")

def test_get_rate_cached(db_session):
    db_session.add(ExchangeRate(rate_date="2000-01-01", source_currency="USD", rate_to_eur=Decimal("1.1")))
    db_session.flush()
    
    fetcher = ECBRateFetcher(db_session)
    # This should not trigger any fetch
    with patch("urllib.request.urlopen") as mock_url:
        assert fetcher.get_rate("USD", "2000-01-01") == Decimal("1.1")
        mock_url.assert_not_called()

def test_get_rate_weekend_fallback(db_session):
    # Friday 2022-01-07 has a rate
    db_session.add(ExchangeRate(rate_date="2022-01-07", source_currency="USD", rate_to_eur=Decimal("1.0921")))
    db_session.flush()
    
    fetcher = ECBRateFetcher(db_session)
    # Saturday 2022-01-08 should fall back to Friday
    assert fetcher.get_rate("USD", "2022-01-08") == Decimal("1.0921")
    # Sunday 2022-01-09 should fall back to Friday
    assert fetcher.get_rate("USD", "2022-01-09") == Decimal("1.0921")

def test_get_rate_fetches_on_miss(db_session):
    fetcher = ECBRateFetcher(db_session)
    
    with patch("urllib.request.urlopen") as mock_url:
        # Mock response
        mock_response = MagicMock()
        mock_response.read.return_value = SAMPLE_CSV_2024.encode('utf-8')
        mock_response.__enter__.return_value = mock_response
        mock_url.return_value = mock_response
        
        # 2024-01-05 is in SAMPLE_CSV
        rate = fetcher.get_rate("USD", "2024-01-05")
        assert rate == Decimal("1.0921")
        
        # Verify it was cached in DB
        stmt = select(ExchangeRate).where(ExchangeRate.rate_date == "2024-01-05")
        cached = db_session.execute(stmt).scalar()
        assert cached.rate_to_eur == Decimal("1.0921")

def test_get_rate_raises_on_not_found(db_session):
    fetcher = ECBRateFetcher(db_session)
    
    with patch("urllib.request.urlopen") as mock_url:
        # Return empty CSV
        mock_response = MagicMock()
        mock_response.read.return_value = b""
        mock_response.__enter__.return_value = mock_response
        mock_url.return_value = mock_response
        
        with pytest.raises(ValueError, match="No ECB rate found"):
            # Use a date that definitely hasn't been used
            fetcher.get_rate("USD", "1990-01-01")

def test_fetch_rates_idempotency(db_session):
    fetcher = ECBRateFetcher(db_session)
    # Pre-add one rate
    db_session.add(ExchangeRate(rate_date="2023-01-05", source_currency="USD", rate_to_eur=Decimal("1.0921")))
    db_session.flush()
    
    with patch("urllib.request.urlopen") as mock_url:
        mock_response = MagicMock()
        mock_response.read.return_value = SAMPLE_CSV_2023.encode('utf-8')
        mock_response.__enter__.return_value = mock_response
        mock_url.return_value = mock_response
        
        # Should only add 2023-01-04 and 2023-01-03
        new_rates = fetcher.fetch_rates("USD", "2023-01-01", "2023-01-10")
        assert len(new_rates) == 2
        dates = [r.rate_date for r in new_rates]
        assert "2023-01-04" in dates
        assert "2023-01-03" in dates
        assert "2023-01-05" not in dates
