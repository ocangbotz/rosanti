"""Simple key/value store for dashboard-editable app settings that aren't
sensitive enough to require `.env` + a restart (e.g. default chart symbol,
active timeframe, UI preferences)."""

from __future__ import annotations

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, IdMixin, TimestampMixin


class AppSetting(IdMixin, TimestampMixin, Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    value: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<AppSetting {self.key}={self.value!r}>"
