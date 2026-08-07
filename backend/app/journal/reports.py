"""Journal reporting: win rate and weekly/monthly performance summaries.

`calculate_win_rate` is a pure function over already-loaded entries so it
can be unit-tested without a database; the weekly/monthly report builders
are the thin DB-aware layer on top that decide the date range and delegate
to `journal.repository.list_entries`.
"""

from __future__ import annotations

import calendar
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.constants import TradeOutcome
from app.database.models.journal import JournalEntry
from app.journal.repository import list_entries
from app.schemas.journal import JournalEntryRead, PeriodReport, WinRateReport

_MAX_ENTRIES_PER_REPORT = 10_000  # effectively "no pagination" for a single period's report


def _pnl(entry: JournalEntry) -> float:
    return entry.profit_loss if entry.profit_loss is not None else 0.0


def calculate_win_rate(entries: list[JournalEntry]) -> WinRateReport:
    closed = [e for e in entries if e.outcome != TradeOutcome.PENDING]
    wins = sum(1 for e in closed if e.outcome == TradeOutcome.WIN)
    losses = sum(1 for e in closed if e.outcome == TradeOutcome.LOSS)
    breakevens = sum(1 for e in closed if e.outcome == TradeOutcome.BREAKEVEN)
    total = len(closed)

    win_rate_percent = round((wins / total * 100), 2) if total > 0 else 0.0
    r_multiples = [e.r_multiple for e in closed if e.r_multiple is not None]
    average_r_multiple = round(sum(r_multiples) / len(r_multiples), 2) if r_multiples else None
    total_profit_loss = round(sum(e.profit_loss or 0.0 for e in closed), 2)

    return WinRateReport(
        total_trades=total,
        wins=wins,
        losses=losses,
        breakevens=breakevens,
        win_rate_percent=win_rate_percent,
        average_r_multiple=average_r_multiple,
        total_profit_loss=total_profit_loss,
    )


def _build_period_report(
    db: Session, start: datetime, end: datetime, account_id: int | None
) -> PeriodReport:
    entries, _ = list_entries(
        db,
        account_id=account_id,
        opened_after=start,
        opened_before=end,
        page=1,
        page_size=_MAX_ENTRIES_PER_REPORT,
    )
    win_rate = calculate_win_rate(entries)
    net_profit_loss = round(sum(e.profit_loss or 0.0 for e in entries), 2)

    closed_with_pnl = [e for e in entries if e.profit_loss is not None]
    best = max(closed_with_pnl, key=_pnl) if closed_with_pnl else None
    worst = min(closed_with_pnl, key=_pnl) if closed_with_pnl else None

    return PeriodReport(
        period_start=start,
        period_end=end,
        trades=[JournalEntryRead.model_validate(e) for e in entries],
        win_rate=win_rate,
        net_profit_loss=net_profit_loss,
        best_trade=JournalEntryRead.model_validate(best) if best else None,
        worst_trade=JournalEntryRead.model_validate(worst) if worst else None,
    )


def get_weekly_report(
    db: Session, account_id: int | None = None, reference_date: datetime | None = None
) -> PeriodReport:
    reference_date = reference_date or datetime.now(UTC)
    start = (reference_date - timedelta(days=reference_date.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    end = start + timedelta(days=7)
    return _build_period_report(db, start, end, account_id)


def get_monthly_report(
    db: Session, account_id: int | None = None, reference_date: datetime | None = None
) -> PeriodReport:
    reference_date = reference_date or datetime.now(UTC)
    start = reference_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    days_in_month = calendar.monthrange(start.year, start.month)[1]
    end = start + timedelta(days=days_in_month)
    return _build_period_report(db, start, end, account_id)
