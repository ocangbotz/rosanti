"""Outbound Telegram notifications: trade lifecycle events, SL/TP hits,
high-impact news warnings, new AI-generated setups, and the daily summary.

Delivery is best-effort per-subscriber: one blocked/invalid chat must not
prevent the rest of the broadcast list from being notified, so failures are
collected and returned rather than raised.
"""

from __future__ import annotations

from telegram import Bot
from telegram.constants import ParseMode
from telegram.error import TelegramError

from app.config import Settings
from app.core.exceptions import TelegramDeliveryError
from app.core.logging_config import get_logger
from app.database.models.journal import JournalEntry
from app.database.models.news import NewsEvent
from app.database.models.setup import TradeSetup
from app.services.telegram.repository import list_subscribers_for

logger = get_logger(__name__)


class BroadcastResult:
    def __init__(self, sent: list[str], failed: list[dict]):
        self.sent = sent
        self.failed = failed

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<BroadcastResult sent={len(self.sent)} failed={len(self.failed)}>"


class TelegramNotifier:
    def __init__(self, settings: Settings, bot: Bot | None = None):
        if bot is None:
            if not settings.telegram_bot_token:
                raise TelegramDeliveryError(
                    "TELEGRAM_BOT_TOKEN is not configured — cannot send Telegram notifications."
                )
            bot = Bot(token=settings.telegram_bot_token)
        self._bot = bot

    async def _broadcast(self, db, message: str, preference_field: str) -> BroadcastResult:
        subscribers = list_subscribers_for(db, preference_field)
        sent: list[str] = []
        failed: list[dict] = []

        for subscriber in subscribers:
            try:
                await self._bot.send_message(
                    chat_id=subscriber.chat_id, text=message, parse_mode=ParseMode.MARKDOWN
                )
                sent.append(subscriber.chat_id)
            except TelegramError as exc:
                logger.warning(
                    "Failed to deliver Telegram message to %s: %s", subscriber.chat_id, exc
                )
                failed.append({"chat_id": subscriber.chat_id, "error": str(exc)})

        return BroadcastResult(sent=sent, failed=failed)

    async def notify_trade_opened(self, db, entry: JournalEntry) -> BroadcastResult:
        message = (
            f"🟢 *Trade Opened*\n"
            f"{entry.symbol} — {entry.direction.value}\n"
            f"Entry: `{entry.entry_price}`\n"
            f"Stop Loss: `{entry.stop_loss}`\n"
            f"Take Profit: `{entry.take_profit}`\n"
            f"Lot size: `{entry.lot_size}`"
        )
        return await self._broadcast(db, message, "notify_trade_opened")

    async def notify_trade_closed(self, db, entry: JournalEntry) -> BroadcastResult:
        emoji = (
            "✅"
            if entry.outcome.value == "WIN"
            else "❌" if entry.outcome.value == "LOSS" else "➖"
        )
        pnl = f"{entry.profit_loss:+.2f}" if entry.profit_loss is not None else "n/a"
        message = (
            f"{emoji} *Trade Closed — {entry.outcome.value}*\n"
            f"{entry.symbol} — {entry.direction.value}\n"
            f"Exit: `{entry.exit_price}`\n"
            f"P&L: `{pnl}`"
            + (f"\nR-multiple: `{entry.r_multiple:.2f}R`" if entry.r_multiple is not None else "")
        )
        return await self._broadcast(db, message, "notify_trade_closed")

    async def notify_sl_tp_hit(self, db, entry: JournalEntry, hit: str) -> BroadcastResult:
        emoji = "🎯" if hit == "TP" else "🛑"
        label = "Take Profit" if hit == "TP" else "Stop Loss"
        message = (
            f"{emoji} *{label} Hit*\n"
            f"{entry.symbol} — {entry.direction.value}\n"
            f"Price: `{entry.exit_price}`"
        )
        return await self._broadcast(db, message, "notify_sl_tp_hit")

    async def notify_high_impact_news(
        self, db, event: NewsEvent, minutes_until: float
    ) -> BroadcastResult:
        message = (
            f"⚠️ *High-Impact News Approaching*\n"
            f"{event.title} ({event.currency or event.country})\n"
            f"In {minutes_until:.0f} minutes\n"
            "Consider avoiding new positions until after the release."
        )
        return await self._broadcast(db, message, "notify_high_impact_news")

    async def notify_new_setup(self, db, setup: TradeSetup) -> BroadcastResult:
        reasons_text = "\n".join(f"• {r['description']}" for r in setup.reasons[:5])
        message = (
            f"📊 *New Trade Setup — {setup.symbol}*\n"
            f"Direction: *{setup.direction.value}*\n"
            f"Confidence: *{setup.confidence_score:.0f}%*\n"
            f"Entry: `{setup.entry_price}` | SL: `{setup.stop_loss}` | TP: `{setup.take_profit}`\n"
            f"Risk/Reward: 1:{setup.risk_reward:.2f}\n\n"
            f"*Reasons:*\n{reasons_text}"
        )
        return await self._broadcast(db, message, "notify_new_setup")

    async def notify_daily_summary(self, db, summary_text: str) -> BroadcastResult:
        message = f"📅 *Daily Summary*\n{summary_text}"
        return await self._broadcast(db, message, "notify_daily_summary")
