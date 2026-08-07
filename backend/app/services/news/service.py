"""DB-backed news filter: persists fetched calendar events and answers the
"is a high-impact event coming up soon" question the risk/dashboard layers
need before letting a trader (or the assistant) act.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.core.constants import NewsImpact
from app.database.models.news import NewsEvent
from app.schemas.news import NewsCheckResponse, NewsWarning
from app.services.news.client import EconomicCalendarClient, RawNewsEvent


def _as_utc(value: datetime) -> datetime:
    """SQLite has no native timezone-aware datetime type, so values read
    back through SQLAlchemy come back naive even though `DateTime(timezone=
    True)` was written with a UTC-aware value — reattach UTC before doing
    arithmetic against an aware `datetime.now(UTC)`. A no-op on Postgres,
    which preserves tzinfo natively."""
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


async def refresh_calendar(db: Session, settings: Settings | None = None) -> list[NewsEvent]:
    """Fetch the latest calendar feed and upsert it into `news_events`,
    keyed on (title, country, event_time) since the public feed has no
    stable event id."""
    settings = settings or get_settings()
    client = EconomicCalendarClient(settings)
    raw_events = await client.fetch_events()

    stored: list[NewsEvent] = []
    for raw in raw_events:
        stored.append(_upsert_event(db, raw))
    db.flush()
    return stored


def _upsert_event(db: Session, raw: RawNewsEvent) -> NewsEvent:
    existing = db.execute(
        select(NewsEvent).where(
            NewsEvent.title == raw.title,
            NewsEvent.country == raw.country,
            NewsEvent.event_time == raw.event_time,
        )
    ).scalar_one_or_none()

    if existing is not None:
        existing.impact = raw.impact
        existing.forecast = raw.forecast
        existing.previous = raw.previous
        existing.actual = raw.actual
        return existing

    event = NewsEvent(
        title=raw.title,
        country=raw.country,
        currency=raw.currency,
        impact=raw.impact,
        event_time=raw.event_time,
        forecast=raw.forecast,
        previous=raw.previous,
        actual=raw.actual,
        source=raw.source,
    )
    db.add(event)
    return event


def get_upcoming_high_impact(
    db: Session, lookahead_minutes: int | None = None, *, now: datetime | None = None
) -> NewsCheckResponse:
    settings = get_settings()
    lookahead = (
        lookahead_minutes
        if lookahead_minutes is not None
        else settings.news_high_impact_lookahead_minutes
    )
    reference = now or datetime.now(UTC)
    window_end = reference + timedelta(minutes=lookahead)

    events = list(
        db.execute(
            select(NewsEvent)
            .where(
                NewsEvent.impact == NewsImpact.HIGH,
                NewsEvent.event_time >= reference,
                NewsEvent.event_time <= window_end,
            )
            .order_by(NewsEvent.event_time.asc())
        ).scalars()
    )

    warnings = [
        NewsWarning(
            id=e.id,
            created_at=e.created_at,
            updated_at=e.updated_at,
            title=e.title,
            currency=e.currency,
            impact=e.impact,
            event_time=_as_utc(e.event_time),
            minutes_until=round((_as_utc(e.event_time) - reference).total_seconds() / 60, 1),
        )
        for e in events
    ]

    return NewsCheckResponse(
        has_high_impact_soon=len(warnings) > 0, lookahead_minutes=lookahead, events=warnings
    )
