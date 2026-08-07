"""Database engine/session factory and the FastAPI `get_db` dependency."""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

settings = get_settings()

_connect_args = {"check_same_thread": False} if settings.is_sqlite else {}

engine = create_engine(
    settings.database_url,
    connect_args=_connect_args,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a request-scoped DB session."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
