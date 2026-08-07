"""Economic calendar client.

Fetches the public ForexFactory-style weekly calendar feed and normalizes
it into a broker/source-agnostic shape. Parsing is intentionally tolerant
of the feed's quirks (impact spelled "High"/"Medium"/"Low"/"Holiday",
`country` actually carrying a currency code) since this is a third-party
JSON feed the project doesn't control.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict

from app.config import Settings
from app.core.constants import HIGH_IMPACT_EVENT_KEYWORDS, NewsImpact
from app.core.exceptions import NewsFeedError

_IMPACT_MAP: dict[str, NewsImpact] = {
    "high": NewsImpact.HIGH,
    "medium": NewsImpact.MEDIUM,
    "med": NewsImpact.MEDIUM,
    "low": NewsImpact.LOW,
    "holiday": NewsImpact.LOW,
    "non-economic": NewsImpact.LOW,
}


class RawNewsEvent(BaseModel):
    """Normalized shape parsed out of the feed, before DB persistence."""

    model_config = ConfigDict(from_attributes=True)

    title: str
    country: str
    currency: str
    impact: NewsImpact
    event_time: datetime
    forecast: str | None = None
    previous: str | None = None
    actual: str | None = None
    source: str = "forexfactory"


def classify_impact(raw_impact: str, title: str) -> NewsImpact:
    """The feed's own impact rating, upgraded to HIGH if the title matches
    one of our known high-impact event keywords (NFP/CPI/FOMC/rate
    decisions/etc.) — feeds are sometimes inconsistent about labeling these,
    and the product spec calls out these specific events explicitly."""
    title_lower = title.lower()
    if any(keyword in title_lower for keyword in HIGH_IMPACT_EVENT_KEYWORDS):
        return NewsImpact.HIGH
    return _IMPACT_MAP.get(raw_impact.strip().lower(), NewsImpact.LOW)


def _parse_event(raw: dict[str, Any]) -> RawNewsEvent | None:
    title = raw.get("title") or raw.get("event")
    country = raw.get("country") or raw.get("currency")
    date_str = raw.get("date") or raw.get("datetime") or raw.get("time")
    if not title or not country or not date_str:
        return None

    try:
        event_time = datetime.fromisoformat(str(date_str).replace("Z", "+00:00"))
    except ValueError:
        return None

    impact = classify_impact(str(raw.get("impact", "")), str(title))

    return RawNewsEvent(
        title=str(title),
        country=str(country).upper(),
        currency=str(country).upper(),
        impact=impact,
        event_time=event_time,
        forecast=_stringify(raw.get("forecast")),
        previous=_stringify(raw.get("previous")),
        actual=_stringify(raw.get("actual")),
    )


def _stringify(value: Any) -> str | None:
    if value is None or value == "":
        return None
    return str(value)


class EconomicCalendarClient:
    def __init__(self, settings: Settings):
        self._url = settings.news_api_url
        self._timeout = 15.0

    async def fetch_events(self) -> list[RawNewsEvent]:
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(self._url)
        except httpx.HTTPError as exc:
            raise NewsFeedError(f"Failed to reach the economic calendar feed: {exc}") from exc

        if response.status_code != 200:
            raise NewsFeedError(
                f"Economic calendar feed returned {response.status_code}: {response.text[:300]}"
            )

        try:
            raw_events = response.json()
        except ValueError as exc:
            raise NewsFeedError("Economic calendar feed did not return valid JSON.") from exc

        if not isinstance(raw_events, list):
            raise NewsFeedError("Economic calendar feed had an unexpected shape (expected a list).")

        events = [_parse_event(raw) for raw in raw_events]
        return [e for e in events if e is not None]
