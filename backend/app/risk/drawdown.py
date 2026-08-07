"""Drawdown tracking: pure peak-to-trough calculation over an equity curve,
kept separate from any DB access so the math is trivially unit-testable.
"""

from __future__ import annotations

from app.core.exceptions import ValidationFailedError
from app.schemas.risk import DrawdownInfo


def calculate_drawdown(
    equity_curve: list[float], max_drawdown_limit_percent: float
) -> DrawdownInfo:
    """Given a chronological list of equity readings, compute the running
    peak, the current drawdown from that peak, and the worst drawdown
    observed anywhere in the series.
    """
    if not equity_curve:
        raise ValidationFailedError("Cannot compute drawdown from an empty equity curve.")

    peak = equity_curve[0]
    max_drawdown_pct = 0.0
    trough_at_max = peak

    for equity in equity_curve:
        peak = max(peak, equity)
        drawdown_pct = ((peak - equity) / peak * 100) if peak > 0 else 0.0
        if drawdown_pct > max_drawdown_pct:
            max_drawdown_pct = drawdown_pct
            trough_at_max = equity

    current_equity = equity_curve[-1]
    current_drawdown_pct = ((peak - current_equity) / peak * 100) if peak > 0 else 0.0

    return DrawdownInfo(
        peak_equity=round(peak, 2),
        trough_equity=round(trough_at_max, 2),
        current_equity=round(current_equity, 2),
        current_drawdown_percent=round(current_drawdown_pct, 2),
        max_drawdown_observed_percent=round(max_drawdown_pct, 2),
        max_drawdown_limit_percent=max_drawdown_limit_percent,
        limit_breached=current_drawdown_pct >= max_drawdown_limit_percent,
    )
