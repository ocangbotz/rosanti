"""Import every model module so `Base.metadata` is fully populated —
required for both `Base.metadata.create_all()` (dev SQLite bootstrap) and
Alembic's `--autogenerate` (see alembic/env.py)."""

from app.database.models.account import AccountSnapshot, BrokerAccount
from app.database.models.journal import JournalEntry, ScreenshotAnalysis
from app.database.models.news import NewsEvent
from app.database.models.risk import DailyPerformance, RiskSettings
from app.database.models.settings import AppSetting
from app.database.models.setup import SetupStatus, TradeSetup
from app.database.models.telegram import TelegramSubscriber

__all__ = [
    "AccountSnapshot",
    "AppSetting",
    "BrokerAccount",
    "DailyPerformance",
    "JournalEntry",
    "NewsEvent",
    "RiskSettings",
    "ScreenshotAnalysis",
    "SetupStatus",
    "TelegramSubscriber",
    "TradeSetup",
]
