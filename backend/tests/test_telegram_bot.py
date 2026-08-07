from datetime import UTC, datetime

import pytest

from app.config import Settings
from app.core.constants import Timeframe, TradeDirection
from app.core.exceptions import FathirError
from app.journal.repository import create_entry, update_entry
from app.schemas.journal import JournalEntryCreate, JournalEntryUpdate
from app.services.telegram.bot import (
    build_analyze_reply,
    build_application,
    build_journal_reply,
    build_positions_reply,
    build_status_reply,
)


@pytest.mark.asyncio
async def test_build_status_reply_includes_account_fields():
    text = await build_status_reply()
    assert "Account Status" in text
    assert "Balance" in text
    assert "Equity" in text


@pytest.mark.asyncio
async def test_build_positions_reply_handles_no_positions():
    text = await build_positions_reply()
    assert "No open positions" in text


@pytest.mark.asyncio
async def test_build_analyze_reply_returns_a_direction_or_rejection():
    text = await build_analyze_reply("EURUSD", Timeframe.H1)
    assert "EURUSD Analysis" in text
    assert "Direction" in text or "No valid setup" in text


@pytest.mark.asyncio
async def test_build_journal_reply_handles_empty_journal(db_session):
    text = await build_journal_reply(db_session)
    assert "No journal entries" in text


@pytest.mark.asyncio
async def test_build_journal_reply_summarizes_recent_trades(db_session):
    entry = create_entry(
        db_session,
        JournalEntryCreate(
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            entry_price=1.1000,
            stop_loss=1.0950,
            take_profit=1.1150,
            lot_size=0.1,
            opened_at=datetime.now(UTC),
        ),
    )
    update_entry(
        db_session,
        entry.id,
        JournalEntryUpdate(exit_price=1.1100, closed_at=datetime.now(UTC), profit_loss=100.0),
    )

    text = await build_journal_reply(db_session)
    assert "Win rate" in text
    assert "EURUSD" in text


def test_build_application_registers_expected_commands():
    settings = Settings(telegram_bot_token="dummy-token-for-application-build")
    app = build_application(settings)

    # CommandHandler stores its trigger words as a frozenset on `.commands`.
    all_commands: set[str] = set()
    for group in app.handlers.values():
        for handler in group:
            all_commands |= getattr(handler, "commands", set())

    assert {"start", "stop", "help", "status", "positions", "analyze", "journal"} <= all_commands


def test_build_application_requires_token():
    with pytest.raises(FathirError):
        build_application(Settings(telegram_bot_token=None))
