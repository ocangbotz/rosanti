import pytest

from app.core.exceptions import ValidationFailedError
from app.risk.breakeven import calculate_breakeven
from app.schemas.risk import BreakevenRequest


def test_buy_trade_reaches_breakeven_at_trigger_r():
    request = BreakevenRequest(
        entry_price=1.1000, stop_loss=1.0950, current_price=1.1050, direction="BUY", trigger_r=1.0
    )
    result = calculate_breakeven(request)
    assert result.current_r_multiple == pytest.approx(1.0)
    assert result.breakeven_reached is True
    assert result.suggested_new_stop_loss == pytest.approx(1.1000)


def test_buy_trade_below_trigger_r_not_yet_breakeven():
    request = BreakevenRequest(
        entry_price=1.1000, stop_loss=1.0950, current_price=1.1020, direction="BUY", trigger_r=1.0
    )
    result = calculate_breakeven(request)
    assert result.current_r_multiple == pytest.approx(0.4)
    assert result.breakeven_reached is False
    assert result.suggested_new_stop_loss is None


def test_sell_trade_reaches_breakeven():
    request = BreakevenRequest(
        entry_price=1.1000, stop_loss=1.1050, current_price=1.0940, direction="SELL", trigger_r=1.0
    )
    result = calculate_breakeven(request)
    assert result.current_r_multiple == pytest.approx(1.2)
    assert result.breakeven_reached is True


def test_invalid_stop_loss_side_is_rejected():
    request = BreakevenRequest(
        entry_price=1.1000, stop_loss=1.1050, current_price=1.1020, direction="BUY", trigger_r=1.0
    )
    with pytest.raises(ValidationFailedError):
        calculate_breakeven(request)
