"""
Centralized application configuration.

All runtime configuration is read from environment variables (see
`.env.example` for the full list). Using `pydantic-settings` gives us
validated, typed config with sane defaults for local development, so the
app can boot with zero configuration in "mock" mode.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = BACKEND_ROOT / "data"
SCREENSHOTS_DIR = DATA_DIR / "screenshots"


class Settings(BaseSettings):
    """Application settings, loaded from environment variables / `.env`."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- General ---
    app_name: str = "Fathir AI Trading Assistant"
    environment: str = Field(default="development")  # development | staging | production
    debug: bool = True
    log_level: str = "INFO"

    # --- API security ---
    # Single-user API key. This is a personal trading tool, not a multi-tenant
    # SaaS product, so a shared-secret header is an intentional, documented
    # trade-off rather than an oversight (see docs/ARCHITECTURE.md §7).
    api_key: str = Field(default="change-me-in-production")
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    # --- Database ---
    database_url: str = Field(default=f"sqlite:///{DATA_DIR / 'fathir.db'}")

    # --- Credential encryption ---
    # Fernet key (32 url-safe base64-encoded bytes). Generate with:
    #   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    credential_encryption_key: str = Field(default="")

    # --- Broker (MT5) ---
    broker_mode: str = Field(default="mock")  # "mt5" | "mock"
    mt5_login: int | None = None
    mt5_password: str | None = None
    mt5_server: str | None = None
    mt5_terminal_path: str | None = None
    mt5_timeout_ms: int = 10_000

    # --- Default trading symbol / timeframe used by background jobs ---
    default_symbol: str = "EURUSD"
    default_timeframe: str = "H1"

    # --- Risk defaults ---
    default_risk_percent: float = 1.0
    default_max_daily_loss_percent: float = 3.0
    default_max_trades_per_day: int = 5
    default_max_drawdown_percent: float = 10.0

    # --- AI / LLM provider ---
    ai_provider: str = "anthropic"
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-4-5-20250929"
    anthropic_vision_model: str = "claude-sonnet-4-5-20250929"
    ai_request_timeout_seconds: float = 30.0

    # --- Telegram ---
    telegram_bot_token: str | None = None
    telegram_default_chat_id: str | None = None
    telegram_enabled: bool = False

    # --- News / economic calendar ---
    news_api_url: str = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
    news_high_impact_lookahead_minutes: int = 60
    news_check_interval_minutes: int = 15

    # --- Scheduler ---
    market_poll_interval_seconds: int = 60
    daily_summary_hour_utc: int = 21

    # --- Uploads ---
    max_screenshot_size_mb: int = 8
    screenshots_dir: Path = SCREENSHOTS_DIR

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("broker_mode")
    @classmethod
    def _validate_broker_mode(cls, value: str) -> str:
        allowed = {"mt5", "mock"}
        if value not in allowed:
            raise ValueError(f"broker_mode must be one of {allowed}, got {value!r}")
        return value

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (env is read once per process)."""
    settings = Settings()
    settings.screenshots_dir.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return settings
