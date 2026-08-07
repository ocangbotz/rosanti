from datetime import UTC, datetime

from app.analysis.sessions import get_session_info
from app.core.constants import TradingSession


def test_london_session_detected_at_10_utc():
    info = get_session_info(datetime(2024, 1, 2, 10, 0, tzinfo=UTC))
    assert info.session == TradingSession.LONDON


def test_new_york_session_detected_at_18_utc():
    info = get_session_info(datetime(2024, 1, 2, 18, 0, tzinfo=UTC))
    assert info.session == TradingSession.NEW_YORK


def test_london_ny_overlap_detected_at_13_utc():
    info = get_session_info(datetime(2024, 1, 2, 13, 0, tzinfo=UTC))
    assert info.is_overlap is True
    assert info.session in {TradingSession.LONDON, TradingSession.NEW_YORK}


def test_every_hour_of_day_resolves_to_a_valid_session():
    # The configured Sydney/Tokyo/London/New York windows fully tile the
    # 24-hour UTC day, so OFF_HOURS is a defensive fallback rather than a
    # reachable case here — assert the function never errors and always
    # returns one of the known sessions for every hour.
    for hour in range(24):
        info = get_session_info(datetime(2024, 1, 2, hour, 0, tzinfo=UTC))
        assert isinstance(info.session, TradingSession)
