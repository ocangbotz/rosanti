import pytest

from app.core.exceptions import NotFoundError
from app.schemas.telegram import TelegramPreferencesUpdate
from app.services.telegram.repository import (
    get_subscriber,
    list_all_active,
    list_subscribers_for,
    subscribe,
    unsubscribe,
    update_preferences,
)


def test_subscribe_creates_new_subscriber(db_session):
    sub = subscribe(db_session, chat_id="111", username="trader1")
    assert sub.id is not None
    assert sub.is_active is True
    assert sub.username == "trader1"


def test_subscribe_is_idempotent_and_reactivates(db_session):
    subscribe(db_session, chat_id="111", username="trader1")
    unsubscribe(db_session, chat_id="111")

    reactivated = subscribe(db_session, chat_id="111", username="trader1-renamed")
    assert reactivated.is_active is True
    assert reactivated.username == "trader1-renamed"

    all_subs = list_all_active(db_session)
    assert len(all_subs) == 1


def test_get_subscriber_raises_for_unknown_chat(db_session):
    with pytest.raises(NotFoundError):
        get_subscriber(db_session, "does-not-exist")


def test_unsubscribe_deactivates(db_session):
    subscribe(db_session, chat_id="222")
    unsubscribe(db_session, chat_id="222")
    sub = get_subscriber(db_session, "222")
    assert sub.is_active is False
    assert list_all_active(db_session) == []


def test_update_preferences_only_changes_provided_fields(db_session):
    subscribe(db_session, chat_id="333")
    updated = update_preferences(
        db_session, "333", TelegramPreferencesUpdate(notify_trade_opened=False)
    )
    assert updated.notify_trade_opened is False
    assert updated.notify_trade_closed is True  # untouched default


def test_list_subscribers_for_filters_by_preference_and_active(db_session):
    subscribe(db_session, chat_id="a")
    subscribe(db_session, chat_id="b")
    update_preferences(db_session, "b", TelegramPreferencesUpdate(notify_new_setup=False))
    subscribe(db_session, chat_id="c")
    unsubscribe(db_session, chat_id="c")

    recipients = list_subscribers_for(db_session, "notify_new_setup")
    chat_ids = {s.chat_id for s in recipients}
    assert chat_ids == {"a"}


def test_list_subscribers_for_rejects_unknown_field(db_session):
    with pytest.raises(ValueError):
        list_subscribers_for(db_session, "not_a_real_field")
