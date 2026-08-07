"""Telegram subscriber management + test-message endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from telegram.error import TelegramError

from app.api.deps import get_db, get_telegram_notifier, require_api_key
from app.core.exceptions import TelegramDeliveryError
from app.database.models.telegram import TelegramSubscriber
from app.schemas.telegram import (
    TelegramPreferencesUpdate,
    TelegramSubscriberCreate,
    TelegramSubscriberRead,
    TelegramTestMessageRequest,
)
from app.services.telegram import repository as telegram_repository
from app.services.telegram.notifier import TelegramNotifier

router = APIRouter(prefix="/telegram", tags=["telegram"], dependencies=[Depends(require_api_key)])


@router.get("/subscribers", response_model=list[TelegramSubscriberRead])
def list_subscribers(db=Depends(get_db)) -> list[TelegramSubscriber]:
    return telegram_repository.list_all_active(db)


@router.post("/subscribers", response_model=TelegramSubscriberRead)
def create_subscriber(data: TelegramSubscriberCreate, db=Depends(get_db)) -> TelegramSubscriber:
    return telegram_repository.subscribe(db, chat_id=data.chat_id, username=data.username)


@router.patch("/subscribers/{chat_id}", response_model=TelegramSubscriberRead)
def patch_subscriber_preferences(
    chat_id: str, data: TelegramPreferencesUpdate, db=Depends(get_db)
) -> TelegramSubscriber:
    return telegram_repository.update_preferences(db, chat_id, data)


@router.delete("/subscribers/{chat_id}", status_code=204, response_model=None)
def remove_subscriber(chat_id: str, db=Depends(get_db)) -> None:
    telegram_repository.unsubscribe(db, chat_id)


@router.post("/test-message")
async def send_test_message(
    request: TelegramTestMessageRequest,
    db=Depends(get_db),
    notifier: TelegramNotifier = Depends(get_telegram_notifier),
) -> dict:
    if request.chat_id:
        try:
            await notifier.send_direct_message(request.chat_id, request.message)
        except TelegramError as exc:
            raise TelegramDeliveryError(f"Failed to send test message: {exc}") from exc
        return {"sent": [request.chat_id], "failed": []}

    result = await notifier.notify_daily_summary(db, request.message)
    return {"sent": result.sent, "failed": result.failed}
