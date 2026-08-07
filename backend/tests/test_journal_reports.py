from datetime import UTC, datetime, timedelta

from app.core.constants import TradeDirection, TradeOutcome
from app.database.models.journal import JournalEntry
from app.journal.reports import calculate_win_rate, get_monthly_report, get_weekly_report
from app.journal.repository import create_entry, update_entry
from app.schemas.journal import JournalEntryCreate, JournalEntryUpdate


def _entry(
    outcome: TradeOutcome, profit_loss: float | None, r_multiple: float | None = None
) -> JournalEntry:
    return JournalEntry(
        symbol="EURUSD",
        direction=TradeDirection.BUY,
        entry_price=1.1,
        stop_loss=1.09,
        take_profit=1.12,
        lot_size=0.1,
        opened_at=datetime.now(UTC),
        outcome=outcome,
        profit_loss=profit_loss,
        r_multiple=r_multiple,
    )


def test_calculate_win_rate_ignores_pending_trades():
    entries = [
        _entry(TradeOutcome.WIN, 100.0, 2.0),
        _entry(TradeOutcome.LOSS, -50.0, -1.0),
        _entry(TradeOutcome.PENDING, None, None),
    ]
    report = calculate_win_rate(entries)
    assert report.total_trades == 2
    assert report.wins == 1
    assert report.losses == 1
    assert report.win_rate_percent == 50.0
    assert report.average_r_multiple == 0.5
    assert report.total_profit_loss == 50.0


def test_calculate_win_rate_handles_no_closed_trades():
    report = calculate_win_rate([_entry(TradeOutcome.PENDING, None)])
    assert report.total_trades == 0
    assert report.win_rate_percent == 0.0
    assert report.average_r_multiple is None


def _make_and_close_entry(db_session, opened_at, profit_loss, account_id=1):
    entry = create_entry(
        db_session,
        JournalEntryCreate(
            account_id=account_id,
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            entry_price=1.1000,
            stop_loss=1.0950,
            take_profit=1.1150,
            lot_size=0.1,
            opened_at=opened_at,
        ),
    )
    return update_entry(
        db_session,
        entry.id,
        JournalEntryUpdate(
            exit_price=1.1000 + profit_loss / 1000, closed_at=opened_at, profit_loss=profit_loss
        ),
    )


def test_weekly_report_only_includes_trades_within_the_week(db_session):
    now = datetime.now(UTC)
    this_week = _make_and_close_entry(db_session, now, 100.0)
    _make_and_close_entry(db_session, now - timedelta(days=30), -50.0)

    report = get_weekly_report(db_session, account_id=1, reference_date=now)
    trade_ids = {t.id for t in report.trades}
    assert this_week.id in trade_ids
    assert report.win_rate.total_trades == 1
    assert report.net_profit_loss == 100.0


def test_monthly_report_includes_best_and_worst_trade(db_session):
    now = datetime.now(UTC)
    best = _make_and_close_entry(db_session, now, 200.0)
    worst = _make_and_close_entry(db_session, now, -80.0)

    report = get_monthly_report(db_session, account_id=1, reference_date=now)
    assert report.best_trade.id == best.id
    assert report.worst_trade.id == worst.id
    assert report.net_profit_loss == 120.0
