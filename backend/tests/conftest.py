"""Shared pytest fixtures."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.database import models  # noqa: F401 -- registers all models on Base.metadata
from app.database.base import Base


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """An isolated in-memory SQLite session, fresh schema per test."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()
