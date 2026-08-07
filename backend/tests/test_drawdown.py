import pytest

from app.core.exceptions import ValidationFailedError
from app.risk.drawdown import calculate_drawdown


def test_drawdown_from_peak_to_trough():
    curve = [10_000, 10_500, 9_800, 10_200]
    info = calculate_drawdown(curve, max_drawdown_limit_percent=10.0)
    # Peak is 10_500, worst point after that peak is 9_800 -> drawdown = 700/10500 = 6.67%
    assert info.peak_equity == 10_500
    assert info.max_drawdown_observed_percent == pytest.approx(6.67, abs=0.01)
    assert info.limit_breached is False


def test_current_drawdown_uses_latest_equity_vs_running_peak():
    curve = [10_000, 11_000, 10_450]
    info = calculate_drawdown(curve, max_drawdown_limit_percent=10.0)
    assert info.current_equity == 10_450
    assert info.current_drawdown_percent == pytest.approx((11_000 - 10_450) / 11_000 * 100)


def test_drawdown_limit_breach_is_flagged():
    curve = [10_000, 8_500]
    info = calculate_drawdown(curve, max_drawdown_limit_percent=10.0)
    assert info.limit_breached is True


def test_monotonically_increasing_equity_has_zero_drawdown():
    curve = [10_000, 10_100, 10_300, 10_800]
    info = calculate_drawdown(curve, max_drawdown_limit_percent=10.0)
    assert info.max_drawdown_observed_percent == 0.0
    assert info.current_drawdown_percent == 0.0
    assert info.limit_breached is False


def test_empty_equity_curve_is_rejected():
    with pytest.raises(ValidationFailedError):
        calculate_drawdown([], max_drawdown_limit_percent=10.0)
