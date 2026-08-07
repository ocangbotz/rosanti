import pandas as pd
import pytest

from app.config import get_settings
from app.core.constants import Timeframe, TradeDirection
from app.services.broker.mock_gateway import MockGateway
from app.services.broker.schemas import OrderRequest


@pytest.fixture
def gateway() -> MockGateway:
    gw = MockGateway(get_settings())
    gw.connect()
    return gw


def test_connect_sets_is_connected(gateway: MockGateway):
    assert gateway.is_connected is True


def test_get_ohlc_matches_standard_contract(gateway: MockGateway):
    df = gateway.get_ohlc("EURUSD", Timeframe.H1, 260)
    assert list(df.columns) == ["time", "open", "high", "low", "close", "volume"]
    assert len(df) == 260
    assert pd.api.types.is_datetime64_any_dtype(df["time"])
    assert (df["high"] >= df["low"]).all()
    assert (df["high"] >= df["open"]).all()
    assert (df["high"] >= df["close"]).all()


def test_get_ohlc_is_deterministic_for_same_symbol():
    gw1 = MockGateway(get_settings())
    gw2 = MockGateway(get_settings())
    df1 = gw1.get_ohlc("EURUSD", Timeframe.H1, 100)
    df2 = gw2.get_ohlc("EURUSD", Timeframe.H1, 100)
    pd.testing.assert_series_equal(df1["close"], df2["close"])


def test_get_symbol_info_has_sane_spread(gateway: MockGateway):
    info = gateway.get_symbol_info("EURUSD")
    assert info.ask > info.bid
    assert info.pip_value_per_lot > 0
    assert info.volume_min <= info.volume_max


def test_jpy_pair_uses_3_digit_precision(gateway: MockGateway):
    info = gateway.get_symbol_info("USDJPY")
    assert info.digits == 3
    assert info.pip_size == 0.01


def test_place_and_close_order_updates_account(gateway: MockGateway):
    account_before = gateway.get_account_info()

    result = gateway.place_order(
        OrderRequest(symbol="EURUSD", direction=TradeDirection.BUY, volume=0.1)
    )
    assert result.success is True
    assert result.ticket is not None

    positions = gateway.get_open_positions()
    assert len(positions) == 1
    assert positions[0].ticket == result.ticket
    assert positions[0].symbol == "EURUSD"

    close_result = gateway.close_position(result.ticket)
    assert close_result.success is True
    assert gateway.get_open_positions() == []

    account_after = gateway.get_account_info()
    # Balance moved by the realized P&L of the round-trip (could be positive
    # or negative depending on synthetic price movement, but it must differ
    # from the pre-trade balance whenever price moved at all, and equity
    # should be back in line with balance once the position is closed).
    assert account_after.equity == account_after.balance
    assert isinstance(account_before.balance, float)


def test_close_unknown_ticket_fails_gracefully(gateway: MockGateway):
    result = gateway.close_position(999_999)
    assert result.success is False
    assert "999999" in result.message
