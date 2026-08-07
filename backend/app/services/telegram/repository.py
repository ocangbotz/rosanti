"""Telegram subscriber persistence: who gets notified, and which categories
of alert they've opted into.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.database.models.telegram import TelegramSubscriber
from app.schemas.telegram import TelegramPreferencesUpdate

# Maps a notification category to the TelegramSubscriber boolean column that
# gates it — used by both the notifier (to select recipients) and the API
# layer (to validate a preference key coming from the dashboard).
PREFERENCE_FIELDS = (
    "notify_trade_opened",
    "notify_trade_closed",
    "notify_sl_tp_hit",
    "notify_high_impact_news",
    "notify_daily_summary",
    "notify_new_setup",
)


def get_subscriber(db: Session, chat_id: str) -> TelegramSubscriber:
    subscriber = db.execute(
        select(TelegramSubscriber).where(TelegramSubscriber.chat_id == chat_id)
    ).scalar_one_or_none()
    if subscriber is None:
        raise NotFoundError(f"No Telegram subscriber found for chat_id={chat_id!r}.")
    return subscriber


def subscribe(db: Session, chat_id: str, username: str | None = None) -> TelegramSubscriber:
    """Idempotent: re-subscribing an existing (possibly deactivated) chat
    reactivates it rather than creating a duplicate row."""
    existing = db.execute(
        select(TelegramSubscriber).where(TelegramSubscriber.chat_id == chat_id)
    ).scalar_one_or_none()

    if existing is not None:
        existing.is_active = True
        if username:
            existing.username = username
        db.flush()
        return existing

    subscriber = TelegramSubscriber(chat_id=chat_id, username=username, is_active=True)
    db.add(subscriber)
    db.flush()
    return subscriber


def unsubscribe(db: Session, chat_id: str) -> TelegramSubscriber:
    subscriber = get_subscriber(db, chat_id)
    subscriber.is_active = False
    db.flush()
    return subscriber


def update_preferences(
    db: Session, chat_id: str, preferences: TelegramPreferencesUpdate
) -> TelegramSubscriber:
    subscriber = get_subscriber(db, chat_id)
    for field, value in preferences.model_dump(exclude_unset=True).items():
        setattr(subscriber, field, value)
    db.flush()
    return subscriber


def list_subscribers_for(db: Session, preference_field: str) -> list[TelegramSubscriber]:
    if preference_field not in PREFERENCE_FIELDS:
        raise ValueError(f"Unknown notification preference field: {preference_field!r}")

    column = getattr(TelegramSubscriber, preference_field)
    return list(
        db.execute(
            select(TelegramSubscriber).where(
                TelegramSubscriber.is_active.is_(True), column.is_(True)
            )
        ).scalars()
    )


def list_all_active(db: Session) -> list[TelegramSubscriber]:
    return list(
        db.execute(
            select(TelegramSubscriber).where(TelegramSubscriber.is_active.is_(True))
        ).scalars()
    )
