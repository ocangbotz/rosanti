from datetime import UTC, datetime, timedelta

import pytest

from app.core.constants import TradeDirection, TradeOutcome
from app.core.exceptions import NotFoundError
from app.journal.repository import (
    add_screenshot,
    create_entry,
    delete_entry,
    get_entry,
    get_screenshot,
    list_entries,
    update_entry,
)
from app.schemas.journal import JournalEntryCreate, JournalEntryUpdate
from app.services.ai.schemas import ScreenshotAnalysisResult


def _make_entry(db_session, **overrides):
    defaults = {
        "symbol": "EURUSD",
        "direction": TradeDirection.BUY,
        "entry_price": 1.1000,
        "stop_loss": 1.0950,
        "take_profit": 1.1150,
        "lot_size": 0.5,
        "opened_at": datetime.now(UTC),
    }
    defaults.update(overrides)
    return create_entry(db_session, JournalEntryCreate(**defaults))


def test_create_entry_defaults_to_pending_outcome(db_session):
    entry = _make_entry(db_session)
    assert entry.id is not None
    assert entry.outcome == TradeOutcome.PENDING
    assert entry.symbol == "EURUSD"


def test_get_entry_raises_for_missing_id(db_session):
    with pytest.raises(NotFoundError):
        get_entry(db_session, 99999)


def test_list_entries_filters_by_symbol_and_account(db_session):
    _make_entry(db_session, symbol="EURUSD", account_id=1)
    _make_entry(db_session, symbol="GBPUSD", account_id=1)
    _make_entry(db_session, symbol="EURUSD", account_id=2)

    items, total = list_entries(db_session, symbol="EURUSD")
    assert total == 2
    assert all(e.symbol == "EURUSD" for e in items)

    items, total = list_entries(db_session, symbol="EURUSD", account_id=1)
    assert total == 1


def test_list_entries_filters_by_date_range(db_session):
    now = datetime.now(UTC)
    _make_entry(db_session, opened_at=now - timedelta(days=10))
    _make_entry(db_session, opened_at=now)

    items, total = list_entries(db_session, opened_after=now - timedelta(days=1))
    assert total == 1


def test_list_entries_paginates(db_session):
    for _ in range(5):
        _make_entry(db_session)

    items, total = list_entries(db_session, page=1, page_size=2)
    assert total == 5
    assert len(items) == 2


def test_update_entry_infers_win_outcome_and_r_multiple(db_session):
    entry = _make_entry(db_session)  # BUY, entry 1.1000, sl 1.0950 (risk = 0.0050)
    updated = update_entry(
        db_session,
        entry.id,
        JournalEntryUpdate(exit_price=1.1100, closed_at=datetime.now(UTC), profit_loss=50.0),
    )
    assert updated.outcome == TradeOutcome.WIN
    # favorable move = 1.1100 - 1.1000 = 0.0100, risk = 0.0050 -> r = 2.0
    assert updated.r_multiple == pytest.approx(2.0)


def test_update_entry_infers_loss_outcome_for_sell(db_session):
    entry = _make_entry(
        db_session, direction=TradeDirection.SELL, entry_price=1.1000, stop_loss=1.1050
    )
    updated = update_entry(
        db_session,
        entry.id,
        JournalEntryUpdate(exit_price=1.1030, closed_at=datetime.now(UTC), profit_loss=-30.0),
    )
    assert updated.outcome == TradeOutcome.LOSS
    # favorable move = 1.1000 - 1.1030 = -0.0030, risk = 0.0050 -> r = -0.6
    assert updated.r_multiple == pytest.approx(-0.6)


def test_update_entry_respects_explicit_outcome_override(db_session):
    entry = _make_entry(db_session)
    updated = update_entry(
        db_session,
        entry.id,
        JournalEntryUpdate(exit_price=1.1000, profit_loss=0.0, outcome=TradeOutcome.BREAKEVEN),
    )
    assert updated.outcome == TradeOutcome.BREAKEVEN


def test_delete_entry_removes_row(db_session):
    entry = _make_entry(db_session)
    delete_entry(db_session, entry.id)
    with pytest.raises(NotFoundError):
        get_entry(db_session, entry.id)


def test_add_screenshot_standalone(db_session):
    result = ScreenshotAnalysisResult(
        detected_trend="bullish",
        detected_support=[1.0950],
        detected_resistance=[1.1050],
        full_report="A clean bullish structure.",
    )
    screenshot = add_screenshot(db_session, result, "/data/screenshots/a.png", symbol_hint="EURUSD")
    assert screenshot.id is not None
    assert screenshot.journal_entry_id is None
    assert screenshot.detected_trend == "bullish"

    fetched = get_screenshot(db_session, screenshot.id)
    assert fetched.file_path == "/data/screenshots/a.png"


def test_add_screenshot_attached_to_entry(db_session):
    entry = _make_entry(db_session)
    result = ScreenshotAnalysisResult(detected_trend="bearish", full_report="Bearish rejection.")
    screenshot = add_screenshot(
        db_session, result, "/data/screenshots/b.png", journal_entry_id=entry.id
    )
    assert screenshot.journal_entry_id == entry.id


def test_add_screenshot_raises_for_missing_journal_entry(db_session):
    result = ScreenshotAnalysisResult(detected_trend="ranging", full_report="Choppy market.")
    with pytest.raises(NotFoundError):
        add_screenshot(db_session, result, "/data/screenshots/c.png", journal_entry_id=99999)


def test_get_screenshot_raises_for_missing_id(db_session):
    with pytest.raises(NotFoundError):
        get_screenshot(db_session, 99999)
