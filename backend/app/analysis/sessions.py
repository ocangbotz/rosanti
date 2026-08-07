"""Trading session tagging (Sydney/Tokyo/London/New York, UTC-based)."""

from __future__ import annotations

from datetime import UTC, datetime

from app.analysis.schemas import SessionInfo
from app.core.constants import SESSION_WINDOWS_UTC, TradingSession


def _hour_in_window(hour: int, window: tuple[int, int]) -> bool:
    start, end = window
    if start < end:
        return start <= hour < end
    return hour >= start or hour < end  # wraps past midnight (e.g. Sydney 21->6)


def get_active_sessions(at: datetime) -> list[TradingSession]:
    hour = at.astimezone(UTC).hour
    return [
        session for session, window in SESSION_WINDOWS_UTC.items() if _hour_in_window(hour, window)
    ]


def get_session_info(at: datetime | None = None) -> SessionInfo:
    """Return the dominant active session as of `at` (defaults to now, UTC).

    When two sessions overlap (e.g. London/New York, historically the
    highest-liquidity window), `is_overlap` is set and the session with
    generally the higher volume of the two is reported as primary.
    """
    as_of = at or datetime.now(UTC)
    active = get_active_sessions(as_of)

    if not active:
        return SessionInfo(session=TradingSession.OFF_HOURS, is_overlap=False, as_of=as_of)

    # Priority order when multiple sessions are simultaneously active,
    # reflecting typical liquidity: London/NY overlap > London > NY > Tokyo > Sydney.
    priority = [
        TradingSession.LONDON,
        TradingSession.NEW_YORK,
        TradingSession.TOKYO,
        TradingSession.SYDNEY,
    ]
    primary = next((s for s in priority if s in active), active[0])
    return SessionInfo(session=primary, is_overlap=len(active) > 1, as_of=as_of)
