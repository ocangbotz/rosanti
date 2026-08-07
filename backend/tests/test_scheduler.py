from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import Settings
from app.database import models  # noqa: F401 -- registers all models on Base.metadata
from app.database.base import Base
from app.database.models.account import AccountSnapshot, BrokerAccount
from app.database.models.news import NewsEvent
from app.database.models.setup import TradeSetup
from app.services.broker.mock_gateway import MockGateway
from app.services.market_data import MarketDataService
from app.services.news.client import EconomicCalendarClient, RawNewsEvent
from app.services.scheduler import TradingScheduler


class _FakeNotifier:
    def __init__(self):
        self.calls: list[tuple] = []

    async def notify_new_setup(self, db, setup):
        self.calls.append(("new_setup", setup.symbol))

    async def notify_high_impact_news(self, db, event, minutes_until):
        self.calls.append(("high_impact_news", event.title, minutes_until))

    async def notify_daily_summary(self, db, summary_text):
        self.calls.append(("daily_summary", summary_text))


@pytest.fixture
def scheduler_sessionmaker(monkeypatch):
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    test_session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    monkeypatch.setattr("app.services.scheduler.SessionLocal", test_session_local)
    yield test_session_local
    engine.dispose()


def _settings(**overrides) -> Settings:
    return Settings(broker_mode="mock", telegram_enabled=True, default_symbol="EURUSD", **overrides)


@pytest.mark.asyncio
async def test_poll_market_records_account_snapshot(scheduler_sessionmaker):
    settings = _settings()
    market_data = MarketDataService(MockGateway(settings))
    notifier = _FakeNotifier()
    scheduler = TradingScheduler(settings, market_data=market_data, notifier=notifier)

    await scheduler.poll_market()

    with scheduler_sessionmaker() as db:
        accounts = db.execute(select(BrokerAccount)).scalars().all()
        snapshots = db.execute(select(AccountSnapshot)).scalars().all()
        assert len(accounts) == 1
        assert len(snapshots) == 1
        assert snapshots[0].account_id == accounts[0].id


@pytest.mark.asyncio
async def test_poll_market_persists_and_announces_new_setup_once(scheduler_sessionmaker):
    settings = _settings()
    market_data = MarketDataService(MockGateway(settings))
    notifier = _FakeNotifier()
    scheduler = TradingScheduler(settings, market_data=market_data, notifier=notifier)

    first = await scheduler.poll_market()
    second = await scheduler.poll_market()

    with scheduler_sessionmaker() as db:
        stored = db.execute(select(TradeSetup)).scalars().all()

    if first is not None:
        assert len(stored) == 1
        # Same signature the second time around (mock market data is
        # deterministic within the same process) -> no duplicate row/alert.
        assert second is None
        assert notifier.calls.count(("new_setup", "EURUSD")) == 1
    else:
        assert stored == []


@pytest.mark.asyncio
async def test_poll_market_survives_broker_errors(scheduler_sessionmaker, monkeypatch):
    settings = _settings()
    market_data = MarketDataService(MockGateway(settings))

    from app.core.exceptions import BrokerUnavailableError

    def raise_broker_error():
        raise BrokerUnavailableError("broker offline")

    monkeypatch.setattr(market_data, "get_account_info", raise_broker_error)
    scheduler = TradingScheduler(settings, market_data=market_data, notifier=_FakeNotifier())

    result = await scheduler.poll_market()
    assert result is None


@pytest.mark.asyncio
async def test_check_news_announces_new_high_impact_event_once(scheduler_sessionmaker, monkeypatch):
    settings = _settings()
    event_time = datetime.now(UTC) + timedelta(minutes=30)

    async def fake_fetch(self):
        return [
            RawNewsEvent(
                title="Non-Farm Payrolls",
                country="USD",
                currency="USD",
                impact="HIGH",
                event_time=event_time,
            )
        ]

    monkeypatch.setattr(EconomicCalendarClient, "fetch_events", fake_fetch)

    notifier = _FakeNotifier()
    scheduler = TradingScheduler(
        settings, market_data=MarketDataService(MockGateway(settings)), notifier=notifier
    )

    await scheduler.check_news()
    await scheduler.check_news()  # second poll should not re-announce the same event

    with scheduler_sessionmaker() as db:
        events = db.execute(select(NewsEvent)).scalars().all()
        assert len(events) == 1

    announcements = [c for c in notifier.calls if c[0] == "high_impact_news"]
    assert len(announcements) == 1
    assert announcements[0][1] == "Non-Farm Payrolls"


@pytest.mark.asyncio
async def test_send_daily_summary_calls_notifier(scheduler_sessionmaker):
    settings = _settings()
    notifier = _FakeNotifier()
    scheduler = TradingScheduler(
        settings, market_data=MarketDataService(MockGateway(settings)), notifier=notifier
    )

    await scheduler.send_daily_summary()

    summaries = [c for c in notifier.calls if c[0] == "daily_summary"]
    assert len(summaries) == 1
    assert "Equity" in summaries[0][1]
