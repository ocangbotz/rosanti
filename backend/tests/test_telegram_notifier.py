from datetime import UTC, datetime

import pytest
from telegram.error import Forbidden

from app.config import Settings
from app.core.constants import TradeDirection, TradeOutcome
from app.core.exceptions import TelegramDeliveryError
from app.database.models.journal import JournalEntry
from app.database.models.news import NewsEvent
from app.database.models.setup import TradeSetup
from app.schemas.telegram import TelegramPreferencesUpdate
from app.services.telegram.notifier import TelegramNotifier
from app.services.telegram.repository import subscribe, update_preferences


class _FakeBot:
    def __init__(self, fail_for: set[str] | None = None):
        self.sent: list[dict] = []
        self.fail_for = fail_for or set()

    async def send_message(self, chat_id, text, parse_mode=None):
        if chat_id in self.fail_for:
            raise Forbidden("bot was blocked by the user")
        self.sent.append({"chat_id": chat_id, "text": text})


def _settings() -> Settings:
    return Settings(telegram_bot_token="dummy-token")


def test_missing_token_raises_without_injected_bot():
    with pytest.raises(TelegramDeliveryError):
        TelegramNotifier(Settings(telegram_bot_token=None))


def test_injected_bot_bypasses_token_requirement():
    notifier = TelegramNotifier(Settings(telegram_bot_token=None), bot=_FakeBot())
    assert notifier is not None


@pytest.mark.asyncio
async def test_notify_trade_opened_sends_to_subscribed_chats(db_session):
    subscribe(db_session, chat_id="1")
    subscribe(db_session, chat_id="2")
    bot = _FakeBot()
    notifier = TelegramNotifier(_settings(), bot=bot)

    entry = JournalEntry(
        symbol="EURUSD",
        direction=TradeDirection.BUY,
        entry_price=1.1,
        stop_loss=1.09,
        take_profit=1.12,
        lot_size=0.1,
        opened_at=datetime.now(UTC),
        outcome=TradeOutcome.PENDING,
    )

    result = await notifier.notify_trade_opened(db_session, entry)

    assert set(result.sent) == {"1", "2"}
    assert result.failed == []
    assert "EURUSD" in bot.sent[0]["text"]


@pytest.mark.asyncio
async def test_notify_respects_per_category_preferences(db_session):
    subscribe(db_session, chat_id="1")
    subscribe(db_session, chat_id="2")
    update_preferences(db_session, "2", TelegramPreferencesUpdate(notify_trade_opened=False))
    bot = _FakeBot()
    notifier = TelegramNotifier(_settings(), bot=bot)

    entry = JournalEntry(
        symbol="EURUSD",
        direction=TradeDirection.BUY,
        entry_price=1.1,
        stop_loss=1.09,
        take_profit=1.12,
        lot_size=0.1,
        opened_at=datetime.now(UTC),
        outcome=TradeOutcome.PENDING,
    )
    result = await notifier.notify_trade_opened(db_session, entry)
    assert result.sent == ["1"]


@pytest.mark.asyncio
async def test_notify_collects_partial_failures_without_raising(db_session):
    subscribe(db_session, chat_id="1")
    subscribe(db_session, chat_id="2")
    bot = _FakeBot(fail_for={"2"})
    notifier = TelegramNotifier(_settings(), bot=bot)

    entry = JournalEntry(
        symbol="EURUSD",
        direction=TradeDirection.SELL,
        entry_price=1.1,
        exit_price=1.09,
        stop_loss=1.11,
        take_profit=1.08,
        lot_size=0.2,
        opened_at=datetime.now(UTC),
        outcome=TradeOutcome.WIN,
        profit_loss=20.0,
        r_multiple=1.0,
    )
    result = await notifier.notify_trade_closed(db_session, entry)

    assert result.sent == ["1"]
    assert result.failed == [{"chat_id": "2", "error": "bot was blocked by the user"}]


@pytest.mark.asyncio
async def test_notify_new_setup_includes_reasons(db_session):
    subscribe(db_session, chat_id="1")
    bot = _FakeBot()
    notifier = TelegramNotifier(_settings(), bot=bot)

    setup = TradeSetup(
        symbol="GBPUSD",
        timeframe="H1",
        direction=TradeDirection.BUY,
        entry_price=1.27,
        stop_loss=1.265,
        take_profit=1.28,
        risk_reward=2.0,
        confidence_score=75.0,
        reasons=[{"factor": "structure_bos", "description": "Bullish BOS confirmed", "weight": 20}],
        structure_snapshot={},
    )
    await notifier.notify_new_setup(db_session, setup)
    assert "Bullish BOS confirmed" in bot.sent[0]["text"]
    assert "GBPUSD" in bot.sent[0]["text"]


@pytest.mark.asyncio
async def test_notify_high_impact_news_formats_message(db_session):
    subscribe(db_session, chat_id="1")
    bot = _FakeBot()
    notifier = TelegramNotifier(_settings(), bot=bot)

    event = NewsEvent(
        title="Non-Farm Payrolls",
        country="USD",
        currency="USD",
        impact="HIGH",
        event_time=datetime.now(UTC),
    )
    await notifier.notify_high_impact_news(db_session, event, minutes_until=42.0)
    assert "Non-Farm Payrolls" in bot.sent[0]["text"]
    assert "42" in bot.sent[0]["text"]
