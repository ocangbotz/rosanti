from datetime import UTC, datetime, timedelta

import pytest

from app.config import get_settings
from app.core.constants import NewsImpact
from app.database.models.news import NewsEvent
from app.services.news.client import EconomicCalendarClient, RawNewsEvent
from app.services.news.service import get_upcoming_high_impact, refresh_calendar


def _seed_event(db_session, *, title, minutes_from_now, impact=NewsImpact.HIGH, currency="USD"):
    event = NewsEvent(
        title=title,
        country=currency,
        currency=currency,
        impact=impact,
        event_time=datetime.now(UTC) + timedelta(minutes=minutes_from_now),
    )
    db_session.add(event)
    db_session.flush()
    return event


def test_get_upcoming_high_impact_only_returns_events_in_window(db_session):
    _seed_event(db_session, title="NFP", minutes_from_now=30)
    _seed_event(db_session, title="Too far out", minutes_from_now=500)
    _seed_event(db_session, title="Already passed", minutes_from_now=-10)
    _seed_event(db_session, title="Low impact soon", minutes_from_now=20, impact=NewsImpact.LOW)

    result = get_upcoming_high_impact(db_session, lookahead_minutes=60)

    assert result.has_high_impact_soon is True
    titles = {e.title for e in result.events}
    assert titles == {"NFP"}


def test_get_upcoming_high_impact_reports_minutes_until(db_session):
    _seed_event(db_session, title="CPI", minutes_from_now=45)
    result = get_upcoming_high_impact(db_session, lookahead_minutes=60)
    assert result.events[0].minutes_until == pytest.approx(45, abs=1)


def test_get_upcoming_high_impact_empty_when_nothing_scheduled(db_session):
    result = get_upcoming_high_impact(db_session, lookahead_minutes=60)
    assert result.has_high_impact_soon is False
    assert result.events == []


def test_get_upcoming_high_impact_uses_default_lookahead_from_settings(db_session):
    default_lookahead = get_settings().news_high_impact_lookahead_minutes
    _seed_event(db_session, title="Within default window", minutes_from_now=default_lookahead - 5)
    result = get_upcoming_high_impact(db_session)
    assert result.lookahead_minutes == default_lookahead
    assert result.has_high_impact_soon is True


@pytest.mark.asyncio
async def test_refresh_calendar_inserts_new_events(db_session, monkeypatch):
    fake_events = [
        RawNewsEvent(
            title="FOMC Statement",
            country="USD",
            currency="USD",
            impact=NewsImpact.HIGH,
            event_time=datetime.now(UTC) + timedelta(hours=2),
        )
    ]

    async def fake_fetch(self):
        return fake_events

    monkeypatch.setattr(EconomicCalendarClient, "fetch_events", fake_fetch)

    stored = await refresh_calendar(db_session)
    assert len(stored) == 1
    assert stored[0].title == "FOMC Statement"

    all_events = db_session.query(NewsEvent).all()
    assert len(all_events) == 1


@pytest.mark.asyncio
async def test_refresh_calendar_upserts_existing_event(db_session, monkeypatch):
    event_time = datetime.now(UTC) + timedelta(hours=1)
    existing = NewsEvent(
        title="CPI m/m",
        country="USD",
        currency="USD",
        impact=NewsImpact.HIGH,
        event_time=event_time,
        forecast="0.2%",
    )
    db_session.add(existing)
    db_session.flush()

    async def fake_fetch(self):
        return [
            RawNewsEvent(
                title="CPI m/m",
                country="USD",
                currency="USD",
                impact=NewsImpact.HIGH,
                event_time=event_time,
                forecast="0.3%",
                actual="0.3%",
            )
        ]

    monkeypatch.setattr(EconomicCalendarClient, "fetch_events", fake_fetch)

    await refresh_calendar(db_session)

    all_events = db_session.query(NewsEvent).all()
    assert len(all_events) == 1
    assert all_events[0].forecast == "0.3%"
    assert all_events[0].actual == "0.3%"
