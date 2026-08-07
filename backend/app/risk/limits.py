"""DB-backed risk limit enforcement: daily loss limit, max trades/day, and
account drawdown — the checks that gate whether a new trade is allowed at
all, independent of how good any individual setup looks.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.exceptions import InsufficientDataError
from app.database.models.account import AccountSnapshot
from app.database.models.risk import DailyPerformance, RiskSettings
from app.risk.drawdown import calculate_drawdown
from app.schemas.risk import DailyLimitCheckResponse, DrawdownInfo


def get_risk_settings(db: Session, account_id: int | None) -> RiskSettings:
    """Account-specific settings win; fall back to a global default row
    (account_id IS NULL), creating it from `.env` defaults on first use."""
    if account_id is not None:
        account_settings = db.execute(
            select(RiskSettings).where(RiskSettings.account_id == account_id)
        ).scalar_one_or_none()
        if account_settings is not None:
            return account_settings

    global_settings = db.execute(
        select(RiskSettings).where(RiskSettings.account_id.is_(None))
    ).scalar_one_or_none()
    if global_settings is not None:
        return global_settings

    settings = get_settings()
    global_settings = RiskSettings(
        account_id=None,
        risk_percent=settings.default_risk_percent,
        max_daily_loss_percent=settings.default_max_daily_loss_percent,
        max_trades_per_day=settings.default_max_trades_per_day,
        max_drawdown_percent=settings.default_max_drawdown_percent,
    )
    db.add(global_settings)
    db.flush()
    return global_settings


def get_or_create_daily_performance(
    db: Session, account_id: int, for_date: date, starting_equity: float
) -> DailyPerformance:
    row = db.execute(
        select(DailyPerformance).where(
            DailyPerformance.account_id == account_id, DailyPerformance.date == for_date
        )
    ).scalar_one_or_none()
    if row is not None:
        return row

    row = DailyPerformance(
        account_id=account_id,
        date=for_date,
        starting_equity=starting_equity,
        realized_pnl=0.0,
        trades_count=0,
    )
    db.add(row)
    db.flush()
    return row


def record_closed_trade(
    db: Session,
    account_id: int,
    pnl: float,
    ending_equity: float,
    closed_at: datetime | None = None,
) -> DailyPerformance:
    """Update the running daily ledger when a journal trade is closed. The
    daily row is created on demand — in normal operation the scheduler
    (app/services/scheduler.py) has already created it from the day's
    opening equity snapshot, so `starting_equity` here is only a fallback
    for the edge case of the very first trade before any snapshot exists.
    """
    trade_date = (closed_at or datetime.now(UTC)).date()
    row = get_or_create_daily_performance(
        db, account_id=account_id, for_date=trade_date, starting_equity=ending_equity - pnl
    )
    row.realized_pnl += pnl
    row.trades_count += 1
    row.ending_equity = ending_equity
    db.flush()
    return row


def check_daily_limits(db: Session, account_id: int) -> DailyLimitCheckResponse:
    risk_settings = get_risk_settings(db, account_id)
    today = datetime.now(UTC).date()
    daily = db.execute(
        select(DailyPerformance).where(
            DailyPerformance.account_id == account_id, DailyPerformance.date == today
        )
    ).scalar_one_or_none()

    trades_taken = daily.trades_count if daily else 0
    realized_pnl = daily.realized_pnl if daily else 0.0
    starting_equity = daily.starting_equity if daily else 0.0
    daily_pnl_percent = (realized_pnl / starting_equity * 100) if starting_equity > 0 else 0.0

    reasons: list[str] = []
    can_trade = True

    if trades_taken >= risk_settings.max_trades_per_day:
        can_trade = False
        reasons.append(
            f"Daily trade limit reached ({trades_taken}/{risk_settings.max_trades_per_day})."
        )

    if daily_pnl_percent <= -risk_settings.max_daily_loss_percent:
        can_trade = False
        reasons.append(
            f"Daily loss limit reached ({daily_pnl_percent:.2f}% <= "
            f"-{risk_settings.max_daily_loss_percent:.2f}%)."
        )

    return DailyLimitCheckResponse(
        can_trade=can_trade,
        trades_taken_today=trades_taken,
        max_trades_per_day=risk_settings.max_trades_per_day,
        daily_pnl_percent=round(daily_pnl_percent, 2),
        max_daily_loss_percent=risk_settings.max_daily_loss_percent,
        reasons=reasons,
    )


def get_drawdown_for_account(db: Session, account_id: int) -> DrawdownInfo:
    risk_settings = get_risk_settings(db, account_id)
    equity_curve = list(
        db.execute(
            select(AccountSnapshot.equity)
            .where(AccountSnapshot.account_id == account_id)
            .order_by(AccountSnapshot.created_at.asc())
        ).scalars()
    )
    if not equity_curve:
        raise InsufficientDataError(
            "No account snapshots recorded yet — drawdown cannot be computed until "
            "at least one balance/equity poll has run."
        )
    return calculate_drawdown(
        equity_curve, max_drawdown_limit_percent=risk_settings.max_drawdown_percent
    )
