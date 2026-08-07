"""Shared FastAPI dependencies: DB session, API key auth."""

from __future__ import annotations

from collections.abc import Generator

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database.session import get_db as _get_db

get_db = _get_db


def get_app_settings() -> Settings:
    return get_settings()


def require_api_key(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    settings: Settings = Depends(get_app_settings),
) -> None:
    """Guard non-public endpoints behind a shared-secret API key.

    This is a single-user personal trading tool (see docs/ARCHITECTURE.md §7),
    so a shared secret header is a deliberate, documented simplification
    rather than a placeholder for "real" auth.
    """
    if settings.environment == "development" and settings.api_key == "change-me-in-production":
        # Zero-config local dev: skip auth entirely until the operator sets a key.
        return
    if not x_api_key or x_api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid API key.",
        )


DbSession = Session
DbDep = Depends(get_db)


def db_session() -> Generator[Session, None, None]:
    yield from _get_db()
