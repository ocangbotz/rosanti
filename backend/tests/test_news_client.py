import httpx
import pytest

from app.config import Settings
from app.core.constants import NewsImpact
from app.core.exceptions import NewsFeedError
from app.services.news.client import EconomicCalendarClient, classify_impact


class _FakeResponse:
    def __init__(self, status_code: int, payload=None, text: str = ""):
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self):
        if self._payload is None:
            raise ValueError("no payload")
        return self._payload


class _FakeAsyncClient:
    response_to_return: _FakeResponse | Exception = _FakeResponse(200, [])

    def __init__(self, timeout=None):
        self.timeout = timeout

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        return False

    async def get(self, url):
        if isinstance(_FakeAsyncClient.response_to_return, Exception):
            raise _FakeAsyncClient.response_to_return
        return _FakeAsyncClient.response_to_return


@pytest.fixture(autouse=True)
def patch_httpx_client(monkeypatch):
    monkeypatch.setattr("app.services.news.client.httpx.AsyncClient", _FakeAsyncClient)
    yield


def _settings() -> Settings:
    return Settings(news_api_url="https://example.test/calendar.json")


def test_classify_impact_upgrades_known_high_impact_titles():
    assert classify_impact("Low", "Non-Farm Payrolls") == NewsImpact.HIGH
    assert classify_impact("Medium", "FOMC Statement") == NewsImpact.HIGH
    assert classify_impact("low", "CPI m/m") == NewsImpact.HIGH


def test_classify_impact_falls_back_to_feed_value_for_unknown_titles():
    assert classify_impact("Low", "Retail Sales") == NewsImpact.LOW
    assert classify_impact("Medium", "Trade Balance") == NewsImpact.MEDIUM
    assert classify_impact("High", "Housing Starts") == NewsImpact.HIGH


def test_classify_impact_defaults_unknown_strings_to_low():
    assert classify_impact("Holiday", "Bank Holiday") == NewsImpact.LOW
    assert classify_impact("garbage", "Some Random Event") == NewsImpact.LOW


@pytest.mark.asyncio
async def test_fetch_events_parses_valid_feed():
    payload = [
        {
            "title": "Non-Farm Payrolls",
            "country": "USD",
            "date": "2026-08-07T12:30:00+00:00",
            "impact": "High",
            "forecast": "180K",
            "previous": "175K",
        },
        {
            "title": "Retail Sales m/m",
            "country": "GBP",
            "date": "2026-08-07T06:00:00+00:00",
            "impact": "Low",
        },
    ]
    _FakeAsyncClient.response_to_return = _FakeResponse(200, payload)
    client = EconomicCalendarClient(_settings())

    events = await client.fetch_events()

    assert len(events) == 2
    nfp = next(e for e in events if e.title == "Non-Farm Payrolls")
    assert nfp.impact == NewsImpact.HIGH
    assert nfp.country == "USD"
    assert nfp.forecast == "180K"


@pytest.mark.asyncio
async def test_fetch_events_skips_malformed_entries():
    payload = [
        {"title": "Missing date", "country": "USD"},
        {
            "title": "Valid Event",
            "country": "EUR",
            "date": "2026-08-07T12:00:00+00:00",
            "impact": "Medium",
        },
    ]
    _FakeAsyncClient.response_to_return = _FakeResponse(200, payload)
    client = EconomicCalendarClient(_settings())

    events = await client.fetch_events()
    assert len(events) == 1
    assert events[0].title == "Valid Event"


@pytest.mark.asyncio
async def test_fetch_events_raises_on_non_200():
    _FakeAsyncClient.response_to_return = _FakeResponse(503, text="service unavailable")
    client = EconomicCalendarClient(_settings())
    with pytest.raises(NewsFeedError):
        await client.fetch_events()


@pytest.mark.asyncio
async def test_fetch_events_raises_on_invalid_json():
    _FakeAsyncClient.response_to_return = _FakeResponse(200, payload=None)
    client = EconomicCalendarClient(_settings())
    with pytest.raises(NewsFeedError):
        await client.fetch_events()


@pytest.mark.asyncio
async def test_fetch_events_raises_on_non_list_payload():
    _FakeAsyncClient.response_to_return = _FakeResponse(200, {"not": "a list"})
    client = EconomicCalendarClient(_settings())
    with pytest.raises(NewsFeedError):
        await client.fetch_events()


@pytest.mark.asyncio
async def test_fetch_events_raises_on_network_error():
    _FakeAsyncClient.response_to_return = httpx.ConnectTimeout("timed out")
    client = EconomicCalendarClient(_settings())
    with pytest.raises(NewsFeedError):
        await client.fetch_events()
