import pytest

from app.core.exceptions import ValidationFailedError
from app.risk.position_sizing import LOT_STEP, MIN_LOT, calculate_lot_size
from app.schemas.risk import LotSizeRequest


def test_lot_size_matches_manual_calculation():
    request = LotSizeRequest(
        account_balance=10_000,
        risk_percent=1.0,
        entry_price=1.1000,
        stop_loss=1.0950,
        symbol="EURUSD",
        pip_value_per_lot=10.0,
        pip_size=0.0001,
    )
    result = calculate_lot_size(request)

    # risk_amount = 100, sl_pips = 50, raw_lot = 100 / (50*10) = 0.2
    assert result.risk_amount == 100.0
    assert result.stop_loss_pips == pytest.approx(50.0)
    assert result.lot_size == pytest.approx(0.2)


def test_lot_size_is_floored_to_lot_step_not_rounded_up():
    request = LotSizeRequest(
        account_balance=1_000,
        risk_percent=1.0,
        entry_price=1.1000,
        stop_loss=1.0950,
        symbol="EURUSD",
        pip_value_per_lot=10.0,
        pip_size=0.0001,
    )
    # risk_amount=10, sl_pips=50, raw_lot=10/(50*10)=0.02 exactly on the step
    result = calculate_lot_size(request)
    assert result.lot_size == pytest.approx(0.02)


def test_lot_size_never_goes_below_minimum():
    request = LotSizeRequest(
        account_balance=50,
        risk_percent=0.1,
        entry_price=1.1000,
        stop_loss=1.0000,
        symbol="EURUSD",
        pip_value_per_lot=10.0,
        pip_size=0.0001,
    )
    result = calculate_lot_size(request)
    assert result.lot_size == MIN_LOT


def test_zero_distance_stop_loss_is_rejected():
    request = LotSizeRequest(
        account_balance=10_000,
        risk_percent=1.0,
        entry_price=1.1000,
        stop_loss=1.1000,
        symbol="EURUSD",
    )
    with pytest.raises(ValidationFailedError):
        calculate_lot_size(request)


def test_lot_size_is_a_multiple_of_lot_step():
    request = LotSizeRequest(
        account_balance=37_500,
        risk_percent=1.7,
        entry_price=1.2345,
        stop_loss=1.2299,
        symbol="GBPUSD",
        pip_value_per_lot=9.3,
        pip_size=0.0001,
    )
    result = calculate_lot_size(request)
    steps = result.lot_size / LOT_STEP
    assert steps == pytest.approx(round(steps))
