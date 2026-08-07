"""Telegram bot commands.

The actual message-formatting logic lives in standalone `build_*_reply`
functions that take plain arguments and return plain strings — this keeps
it fully unit-testable without constructing python-telegram-bot `Update`/
`Context` objects. The `cmd_*` functions are thin adapters that PTB calls
directly, pulling arguments out of `Update`/`Context` and delegating.
"""

from __future__ import annotations

from telegram import Message, Update
from telegram.constants import ParseMode
from telegram.ext import Application, ApplicationBuilder, CommandHandler, ContextTypes

from app.analysis.engine import MarketAnalysisEngine
from app.config import Settings, get_settings
from app.core.constants import Timeframe
from app.core.exceptions import FathirError
from app.core.logging_config import get_logger
from app.database.session import SessionLocal
from app.journal.reports import calculate_win_rate
from app.journal.repository import list_entries
from app.services.broker.factory import get_broker_gateway
from app.services.market_data import MarketDataService
from app.services.telegram import repository as telegram_repository
from app.strategies.setup_generator import TradeSetupGenerator

logger = get_logger(__name__)


def _message(update: Update) -> Message:
    """CommandHandlers only ever fire on updates carrying a message, but
    PTB's typing marks `Update.message` Optional (it covers every update
    kind). Assert the invariant instead of threading `| None` everywhere."""
    assert update.message is not None
    return update.message


def _chat_id(update: Update) -> str:
    assert update.effective_chat is not None
    return str(update.effective_chat.id)


WELCOME_TEXT = (
    "👋 *Welcome to Fathir AI Trading Assistant*\n\n"
    "You're now subscribed to trade alerts. Available commands:\n"
    "/status — account balance, equity, and open positions\n"
    "/positions — list open positions\n"
    "/analyze SYMBOL [TIMEFRAME] — run a full market analysis (e.g. `/analyze EURUSD H1`)\n"
    "/journal — recent trades and win rate\n"
    "/stop — unsubscribe from alerts\n"
    "/help — show this message again"
)


async def build_status_reply() -> str:
    market_data = MarketDataService(get_broker_gateway())
    account = market_data.get_account_info()
    positions = market_data.get_open_positions()

    return (
        "💰 *Account Status*\n"
        f"Login: `{account.login}` ({account.server})\n"
        f"Balance: `{account.balance:,.2f} {account.currency}`\n"
        f"Equity: `{account.equity:,.2f} {account.currency}`\n"
        f"Margin: `{account.margin:,.2f}` | Free: `{account.free_margin:,.2f}`\n"
        f"Open positions: `{len(positions)}`"
    )


async def build_positions_reply() -> str:
    market_data = MarketDataService(get_broker_gateway())
    positions = market_data.get_open_positions()

    if not positions:
        return "📭 No open positions."

    lines = ["📈 *Open Positions*"]
    for pos in positions:
        lines.append(
            f"{pos.symbol} {pos.direction.value} `{pos.volume}` lots — " f"P&L: `{pos.profit:+.2f}`"
        )
    return "\n".join(lines)


async def build_analyze_reply(symbol: str, timeframe: Timeframe = Timeframe.H1) -> str:
    market_data = MarketDataService(get_broker_gateway())
    df = market_data.get_ohlc(symbol.upper(), timeframe, 300)
    analysis = MarketAnalysisEngine().analyze(df, symbol.upper(), timeframe)
    result = TradeSetupGenerator().generate(analysis)

    header = f"📊 *{symbol.upper()} Analysis* ({timeframe.value})"
    if not result.has_valid_setup or result.setup is None:
        return f"{header}\nNo valid setup right now.\n_{result.rejection_reason}_"

    setup = result.setup
    lines = [
        header,
        f"Direction: *{setup.direction.value}*",
        f"Confidence: *{setup.confidence_score:.0f}%*",
        f"Entry: `{setup.entry_price}` | SL: `{setup.stop_loss}` | TP: `{setup.take_profit}`",
        f"Risk/Reward: 1:{setup.risk_reward:.2f}",
        "",
        "*Reasons:*",
    ]
    lines.extend(f"• {r.description}" for r in setup.reasons)
    return "\n".join(lines)


async def build_journal_reply(db, account_id: int | None = None, limit: int = 5) -> str:
    entries, total = list_entries(db, account_id=account_id, page=1, page_size=limit)
    if not entries:
        return "📭 No journal entries yet."

    win_rate = calculate_win_rate(entries)
    lines = [
        "📓 *Recent Trades*",
        f"Win rate (last {len(entries)}): *{win_rate.win_rate_percent:.0f}%* "
        f"({win_rate.wins}W / {win_rate.losses}L / {win_rate.breakevens}BE)",
        "",
    ]
    for entry in entries:
        outcome_emoji = {"WIN": "✅", "LOSS": "❌", "BREAKEVEN": "➖", "PENDING": "⏳"}[
            entry.outcome.value
        ]
        pnl = f"{entry.profit_loss:+.2f}" if entry.profit_loss is not None else "open"
        lines.append(f"{outcome_emoji} {entry.symbol} {entry.direction.value} — `{pnl}`")
    return "\n".join(lines)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    db = SessionLocal()
    try:
        user = update.effective_user
        telegram_repository.subscribe(
            db, chat_id=_chat_id(update), username=user.username if user else None
        )
        db.commit()
    finally:
        db.close()
    await _message(update).reply_text(WELCOME_TEXT, parse_mode=ParseMode.MARKDOWN)


async def cmd_stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    db = SessionLocal()
    try:
        telegram_repository.unsubscribe(db, chat_id=_chat_id(update))
        db.commit()
    finally:
        db.close()
    await _message(update).reply_text(
        "You've been unsubscribed from alerts. Send /start to rejoin."
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _message(update).reply_text(WELCOME_TEXT, parse_mode=ParseMode.MARKDOWN)


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        text = await build_status_reply()
    except FathirError as exc:
        text = f"⚠️ Could not fetch account status: {exc.message}"
    await _message(update).reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def cmd_positions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        text = await build_positions_reply()
    except FathirError as exc:
        text = f"⚠️ Could not fetch positions: {exc.message}"
    await _message(update).reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def cmd_analyze(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args or []
    if not args:
        await _message(update).reply_text(
            "Usage: /analyze SYMBOL [TIMEFRAME] (e.g. /analyze EURUSD H1)"
        )
        return

    symbol = args[0]
    timeframe = Timeframe.H1
    if len(args) > 1:
        try:
            timeframe = Timeframe(args[1].upper())
        except ValueError:
            valid = ", ".join(t.value for t in Timeframe)
            await _message(update).reply_text(
                f"Unknown timeframe {args[1]!r}. Valid options: {valid}"
            )
            return

    try:
        text = await build_analyze_reply(symbol, timeframe)
    except FathirError as exc:
        text = f"⚠️ Analysis failed: {exc.message}"
    await _message(update).reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def cmd_journal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    db = SessionLocal()
    try:
        text = await build_journal_reply(db)
    except FathirError as exc:
        text = f"⚠️ Could not fetch journal: {exc.message}"
    finally:
        db.close()
    await _message(update).reply_text(text, parse_mode=ParseMode.MARKDOWN)


def build_application(settings: Settings | None = None) -> Application:
    settings = settings or get_settings()
    if not settings.telegram_bot_token:
        raise FathirError("TELEGRAM_BOT_TOKEN is not configured.")

    application = ApplicationBuilder().token(settings.telegram_bot_token).build()
    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("stop", cmd_stop))
    application.add_handler(CommandHandler("help", cmd_help))
    application.add_handler(CommandHandler("status", cmd_status))
    application.add_handler(CommandHandler("positions", cmd_positions))
    application.add_handler(CommandHandler("analyze", cmd_analyze))
    application.add_handler(CommandHandler("journal", cmd_journal))
    return application
