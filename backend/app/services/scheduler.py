"""Background jobs: market polling (new setup detection + account/risk
snapshotting), economic calendar refresh + high-impact warnings, and the
daily performance summary.

Every dependency the jobs need (market data, notifier) is injectable via
the constructor — defaulting to the real singletons — specifically so the
job logic can be unit-tested by calling e.g. `await scheduler.poll_market()`
directly against a `MockGateway`, without spinning up APScheduler's actual
timers (which is third-party, well-tested machinery not worth re-testing
here).
"""

from __future__ import annotations

from datetime import UTC, datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analysis.engine import MarketAnalysisEngine
from app.config import Settings, get_settings
from app.core.constants import Timeframe
from app.core.exceptions import FathirError
from app.core.logging_config import get_logger
from app.database.models.account import AccountSnapshot, BrokerAccount
from app.database.models.news import NewsEvent
from app.database.models.setup import SetupStatus, TradeSetup
from app.database.session import SessionLocal
from app.journal.reports import calculate_win_rate
from app.journal.repository import list_entries
from app.risk.limits import get_or_create_daily_performance
from app.schemas.account import LiveAccountInfo
from app.services.broker.factory import get_broker_gateway
from app.services.market_data import MarketDataService
from app.services.news.service import get_upcoming_high_impact, refresh_calendar
from app.services.telegram.notifier import TelegramNotifier
from app.strategies.setup_generator import TradeSetupGenerator

logger = get_logger(__name__)


class TradingScheduler:
    def __init__(
        self,
        settings: Settings | None = None,
        market_data: MarketDataService | None = None,
        notifier: TelegramNotifier | None = None,
    ):
        self._settings = settings or get_settings()
        self._market_data = market_data or MarketDataService(get_broker_gateway())
        self._injected_notifier = notifier
        self._scheduler = AsyncIOScheduler(timezone="UTC")
        # In-memory de-dupe so the same news event / identical setup doesn't
        # trigger a fresh Telegram alert on every poll — acceptable to reset
        # on process restart, unlike the persisted domain data.
        self._notified_news_event_ids: set[int] = set()
        self._last_setup_signature: dict[tuple[str, str], tuple] = {}

    def _get_notifier(self) -> TelegramNotifier | None:
        if self._injected_notifier is not None:
            return self._injected_notifier
        if not self._settings.telegram_enabled:
            return None
        try:
            return TelegramNotifier(self._settings)
        except FathirError as exc:
            logger.warning("Telegram notifier unavailable: %s", exc.message)
            return None

    def start(self) -> None:
        s = self._settings
        self._scheduler.add_job(
            self.poll_market,
            IntervalTrigger(seconds=s.market_poll_interval_seconds),
            id="poll_market",
            replace_existing=True,
            max_instances=1,
        )
        self._scheduler.add_job(
            self.check_news,
            IntervalTrigger(minutes=s.news_check_interval_minutes),
            id="check_news",
            replace_existing=True,
            max_instances=1,
        )
        self._scheduler.add_job(
            self.send_daily_summary,
            CronTrigger(hour=s.daily_summary_hour_utc, minute=0),
            id="daily_summary",
            replace_existing=True,
            max_instances=1,
        )
        self._scheduler.start()
        logger.info("Trading scheduler started.")

    def shutdown(self) -> None:
        self._scheduler.shutdown(wait=False)

    def _ensure_account_row(self, db: Session, info: LiveAccountInfo) -> BrokerAccount:
        account = db.execute(
            select(BrokerAccount).where(
                BrokerAccount.login == info.login, BrokerAccount.server == info.server
            )
        ).scalar_one_or_none()
        if account is None:
            account = BrokerAccount(
                login=info.login, server=info.server, currency=info.currency, leverage=info.leverage
            )
            db.add(account)
            db.flush()
        return account

    def _record_snapshot(self, db: Session, account: BrokerAccount, info: LiveAccountInfo) -> None:
        db.add(
            AccountSnapshot(
                account_id=account.id,
                balance=info.balance,
                equity=info.equity,
                margin=info.margin,
                free_margin=info.free_margin,
                margin_level=info.margin_level,
            )
        )
        get_or_create_daily_performance(
            db, account.id, datetime.now(UTC).date(), starting_equity=info.equity
        )
        db.flush()

    async def poll_market(self) -> TradeSetup | None:
        """Pull the latest OHLC for the default watchlist symbol, record an
        account/risk snapshot, and persist+announce a new setup if the
        confluence engine found one that differs from the last one seen."""
        db = SessionLocal()
        try:
            account_info = self._market_data.get_account_info()
            account = self._ensure_account_row(db, account_info)
            self._record_snapshot(db, account, account_info)

            symbol = self._settings.default_symbol
            timeframe = Timeframe(self._settings.default_timeframe)
            df = self._market_data.get_ohlc(symbol, timeframe)
            analysis = MarketAnalysisEngine().analyze(df, symbol, timeframe)
            result = TradeSetupGenerator().generate(analysis)

            new_setup_row: TradeSetup | None = None
            if result.has_valid_setup and result.setup is not None:
                setup = result.setup
                signature = (setup.direction.value, round(setup.entry_price, 5))
                key = (symbol, timeframe.value)
                if self._last_setup_signature.get(key) != signature:
                    self._last_setup_signature[key] = signature
                    new_setup_row = TradeSetup(
                        symbol=setup.symbol,
                        timeframe=setup.timeframe,
                        direction=setup.direction,
                        entry_price=setup.entry_price,
                        stop_loss=setup.stop_loss,
                        take_profit=setup.take_profit,
                        risk_reward=setup.risk_reward,
                        confidence_score=setup.confidence_score,
                        reasons=[r.model_dump(mode="json") for r in setup.reasons],
                        structure_snapshot=setup.structure_snapshot,
                        status=SetupStatus.PROPOSED,
                    )
                    db.add(new_setup_row)
                    db.flush()

            db.commit()

            if new_setup_row is not None:
                notifier = self._get_notifier()
                if notifier is not None:
                    await notifier.notify_new_setup(db, new_setup_row)

            return new_setup_row
        except FathirError as exc:
            logger.warning("poll_market job failed: %s", exc.message)
            db.rollback()
            return None
        finally:
            db.close()

    async def check_news(self) -> None:
        """Refresh the economic calendar and announce any newly-entering
        high-impact events within the configured lookahead window."""
        db = SessionLocal()
        try:
            await refresh_calendar(db, self._settings)
            db.commit()

            check = get_upcoming_high_impact(db, self._settings.news_high_impact_lookahead_minutes)
            notifier = self._get_notifier()
            if notifier is None:
                return

            for warning in check.events:
                if warning.id in self._notified_news_event_ids:
                    continue
                event = db.get(NewsEvent, warning.id)
                if event is None:
                    continue
                self._notified_news_event_ids.add(warning.id)
                await notifier.notify_high_impact_news(db, event, warning.minutes_until)
        except FathirError as exc:
            logger.warning("check_news job failed: %s", exc.message)
            db.rollback()
        finally:
            db.close()

    async def send_daily_summary(self) -> None:
        db = SessionLocal()
        try:
            today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
            entries, _ = list_entries(db, opened_after=today_start, page=1, page_size=1000)
            win_rate = calculate_win_rate(entries)
            account_info = self._market_data.get_account_info()

            summary = (
                f"Equity: `{account_info.equity:,.2f} {account_info.currency}`\n"
                f"Trades today: `{win_rate.total_trades}` "
                f"({win_rate.wins}W / {win_rate.losses}L / {win_rate.breakevens}BE)\n"
                f"Win rate: `{win_rate.win_rate_percent:.0f}%`\n"
                f"P&L today: `{win_rate.total_profit_loss:+.2f}`"
            )

            notifier = self._get_notifier()
            if notifier is not None:
                await notifier.notify_daily_summary(db, summary)
        except FathirError as exc:
            logger.warning("send_daily_summary job failed: %s", exc.message)
        finally:
            db.close()
