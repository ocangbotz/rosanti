from datetime import UTC, datetime

import pytest

from app.core.exceptions import InsufficientDataError
from app.database.models.account import AccountSnapshot, BrokerAccount
from app.database.models.risk import RiskSettings
from app.risk.limits import (
    check_daily_limits,
    get_drawdown_for_account,
    get_or_create_daily_performance,
    get_risk_settings,
    record_closed_trade,
)


def _make_account(db_session) -> BrokerAccount:
    account = BrokerAccount(login=12345, server="Demo-Server", currency="USD", leverage=100)
    db_session.add(account)
    db_session.flush()
    return account


def test_get_risk_settings_creates_global_default_when_none_exist(db_session):
    settings = get_risk_settings(db_session, account_id=None)
    assert settings.account_id is None
    assert settings.risk_percent > 0
    assert settings.max_trades_per_day > 0


def test_get_risk_settings_prefers_account_specific_row(db_session):
    account = _make_account(db_session)
    db_session.add(
        RiskSettings(account_id=account.id, risk_percent=2.5, max_daily_loss_percent=5.0)
    )
    db_session.flush()

    settings = get_risk_settings(db_session, account_id=account.id)
    assert settings.risk_percent == 2.5


def test_check_daily_limits_allows_trading_with_no_history(db_session):
    account = _make_account(db_session)
    result = check_daily_limits(db_session, account_id=account.id)
    assert result.can_trade is True
    assert result.trades_taken_today == 0
    assert result.reasons == []


def test_check_daily_limits_blocks_after_max_trades(db_session):
    account = _make_account(db_session)
    db_session.add(RiskSettings(account_id=account.id, max_trades_per_day=2))
    db_session.flush()

    today = datetime.now(UTC).date()
    get_or_create_daily_performance(db_session, account.id, today, starting_equity=10_000)
    for _ in range(2):
        record_closed_trade(db_session, account.id, pnl=10.0, ending_equity=10_010)

    result = check_daily_limits(db_session, account_id=account.id)
    assert result.can_trade is False
    assert any("trade limit" in r for r in result.reasons)


def test_check_daily_limits_blocks_after_daily_loss_limit(db_session):
    account = _make_account(db_session)
    db_session.add(RiskSettings(account_id=account.id, max_daily_loss_percent=2.0))
    db_session.flush()

    today = datetime.now(UTC).date()
    get_or_create_daily_performance(db_session, account.id, today, starting_equity=10_000)
    record_closed_trade(db_session, account.id, pnl=-300.0, ending_equity=9_700)

    result = check_daily_limits(db_session, account_id=account.id)
    assert result.can_trade is False
    assert any("loss limit" in r for r in result.reasons)


def test_get_drawdown_for_account_raises_without_snapshots(db_session):
    account = _make_account(db_session)
    with pytest.raises(InsufficientDataError):
        get_drawdown_for_account(db_session, account_id=account.id)


def test_get_drawdown_for_account_computes_from_snapshots(db_session):
    account = _make_account(db_session)
    db_session.add(RiskSettings(account_id=account.id, max_drawdown_percent=15.0))
    for equity in (10_000, 10_500, 9_900):
        db_session.add(
            AccountSnapshot(
                account_id=account.id, balance=equity, equity=equity, margin=0, free_margin=equity
            )
        )
    db_session.flush()

    info = get_drawdown_for_account(db_session, account_id=account.id)
    assert info.peak_equity == 10_500
    assert info.limit_breached is False
