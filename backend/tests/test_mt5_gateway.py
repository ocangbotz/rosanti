"""Tests for MT5Gateway.

The `MetaTrader5` package only installs on Windows against a live
terminal, so it can't be exercised for real here. Two things are tested
instead: (1) the graceful-degradation path when the package genuinely
isn't importable, and (2) the gateway's own mapping logic (MT5 field names
-> our schemas), verified against a hand-built fake module injected into
`sys.modules` — this exercises every line of `mt5_gateway.py` without
needing Windows or a broker connection.
"""

from __future__ import annotations

import sys
import types
from datetime import UTC, datetime

import pytest

from app.config import get_settings
from app.core.constants import Timeframe, TradeDirection
from app.core.exceptions import BrokerConnectionError, BrokerUnavailableError, SymbolNotFoundError
from app.services.broker.mt5_gateway import MT5Gateway
from app.services.broker.schemas import OrderRequest


def test_connect_without_package_installed_raises_broker_unavailable(monkeypatch):
    monkeypatch.delitem(sys.modules, "MetaTrader5", raising=False)
    monkeypatch.setattr(
        "builtins.__import__",
        _blocking_import_for("MetaTrader5"),
    )
    gateway = MT5Gateway(get_settings())
    with pytest.raises(BrokerUnavailableError):
        gateway.connect()


def _blocking_import_for(blocked_name: str):
    real_import = __import__

    def fake_import(name, *args, **kwargs):
        if name == blocked_name:
            raise ImportError(f"No module named {blocked_name!r}")
        return real_import(name, *args, **kwargs)

    return fake_import


class _FakeMT5:
    """Minimal stand-in for the MetaTrader5 SDK surface MT5Gateway uses."""

    TIMEFRAME_M1 = 1
    TIMEFRAME_M5 = 5
    TIMEFRAME_M15 = 15
    TIMEFRAME_M30 = 30
    TIMEFRAME_H1 = 16385
    TIMEFRAME_H4 = 16388
    TIMEFRAME_D1 = 16408
    TIMEFRAME_W1 = 32769

    ORDER_TYPE_BUY = 0
    ORDER_TYPE_SELL = 1
    TRADE_ACTION_DEAL = 1
    ORDER_TIME_GTC = 0
    ORDER_FILLING_IOC = 1
    TRADE_RETCODE_DONE = 10009

    def __init__(self):
        self.initialized = False
        self._positions = [
            types.SimpleNamespace(
                ticket=555,
                symbol="EURUSD",
                type=0,
                volume=0.5,
                price_open=1.1000,
                price_current=1.1050,
                sl=1.0950,
                tp=1.1150,
                profit=25.0,
                swap=-0.5,
                time=int(datetime(2024, 1, 1, tzinfo=UTC).timestamp()),
            )
        ]
        self.last_order_request = None

    def initialize(self, **kwargs):
        self.initialized = True
        return True

    def last_error(self):
        return (0, "no error")

    def shutdown(self):
        self.initialized = False

    def copy_rates_from_pos(self, symbol, timeframe, start_pos, count):
        if symbol == "UNKNOWN":
            return None
        base_time = int(datetime(2024, 1, 1, tzinfo=UTC).timestamp())
        return [
            {
                "time": base_time + i * 3600,
                "open": 1.1000 + i * 0.0001,
                "high": 1.1005 + i * 0.0001,
                "low": 1.0995 + i * 0.0001,
                "close": 1.1002 + i * 0.0001,
                "tick_volume": 1000 + i,
            }
            for i in range(count)
        ]

    def symbol_info(self, symbol):
        if symbol == "UNKNOWN":
            return None
        return types.SimpleNamespace(
            point=0.00001,
            digits=5,
            spread=12,
            trade_contract_size=100_000.0,
            volume_min=0.01,
            volume_max=100.0,
            volume_step=0.01,
        )

    def symbol_info_tick(self, symbol):
        if symbol == "UNKNOWN":
            return None
        return types.SimpleNamespace(bid=1.10495, ask=1.10510)

    def order_calc_profit(self, order_type, symbol, volume, price_open, price_close):
        return abs(price_close - price_open) * 100_000.0 * volume

    def account_info(self):
        return types.SimpleNamespace(
            login=12345,
            server="Demo-Server",
            currency="USD",
            leverage=100,
            balance=10_000.0,
            equity=10_025.0,
            margin=550.0,
            margin_free=9_475.0,
            margin_level=1822.7,
            profit=25.0,
        )

    def positions_get(self, symbol=None, ticket=None):
        if ticket is not None:
            return tuple(p for p in self._positions if p.ticket == ticket)
        return tuple(self._positions)

    def order_send(self, request):
        self.last_order_request = request
        return types.SimpleNamespace(
            retcode=self.TRADE_RETCODE_DONE,
            order=777,
            price=request["price"],
            comment="Request executed",
        )


@pytest.fixture
def fake_mt5(monkeypatch) -> _FakeMT5:
    fake = _FakeMT5()
    monkeypatch.setitem(sys.modules, "MetaTrader5", fake)
    return fake


@pytest.fixture
def connected_gateway(fake_mt5: _FakeMT5) -> MT5Gateway:
    gateway = MT5Gateway(get_settings())
    gateway.connect()
    return gateway


def test_connect_success_sets_is_connected(connected_gateway: MT5Gateway):
    assert connected_gateway.is_connected is True


def test_connect_failure_raises_broker_connection_error(fake_mt5: _FakeMT5, monkeypatch):
    monkeypatch.setattr(fake_mt5, "initialize", lambda **kwargs: False)
    monkeypatch.setattr(fake_mt5, "last_error", lambda: (10013, "Invalid credentials"))
    gateway = MT5Gateway(get_settings())
    with pytest.raises(BrokerConnectionError):
        gateway.connect()


def test_get_ohlc_maps_tick_volume_to_volume(connected_gateway: MT5Gateway):
    df = connected_gateway.get_ohlc("EURUSD", Timeframe.H1, 5)
    assert list(df.columns) == ["time", "open", "high", "low", "close", "volume"]
    assert len(df) == 5
    assert df["volume"].iloc[0] == 1000


def test_get_ohlc_raises_for_unknown_symbol(connected_gateway: MT5Gateway):
    with pytest.raises(SymbolNotFoundError):
        connected_gateway.get_ohlc("UNKNOWN", Timeframe.H1, 5)


def test_get_symbol_info_uses_order_calc_profit_for_pip_value(connected_gateway: MT5Gateway):
    info = connected_gateway.get_symbol_info("EURUSD")
    assert info.bid == 1.10495
    assert info.ask == 1.10510
    assert info.pip_value_per_lot == pytest.approx(0.0001 * 100_000.0, rel=1e-6)


def test_get_account_info_maps_fields(connected_gateway: MT5Gateway):
    info = connected_gateway.get_account_info()
    assert info.login == 12345
    assert info.balance == 10_000.0
    assert info.margin_level == pytest.approx(1822.7)


def test_get_open_positions_maps_buy_type(connected_gateway: MT5Gateway):
    positions = connected_gateway.get_open_positions()
    assert len(positions) == 1
    assert positions[0].direction == TradeDirection.BUY
    assert positions[0].ticket == 555


def test_place_order_sends_correct_request(connected_gateway: MT5Gateway, fake_mt5: _FakeMT5):
    result = connected_gateway.place_order(
        OrderRequest(
            symbol="EURUSD",
            direction=TradeDirection.BUY,
            volume=0.1,
            stop_loss=1.09,
            take_profit=1.12,
        )
    )
    assert result.success is True
    assert result.ticket == 777
    assert fake_mt5.last_order_request["type"] == fake_mt5.ORDER_TYPE_BUY
    assert fake_mt5.last_order_request["volume"] == 0.1


def test_close_position_sends_opposite_order(connected_gateway: MT5Gateway, fake_mt5: _FakeMT5):
    result = connected_gateway.close_position(555)
    assert result.success is True
    # The open position is a BUY, so closing it must send a SELL.
    assert fake_mt5.last_order_request["type"] == fake_mt5.ORDER_TYPE_SELL
    assert fake_mt5.last_order_request["position"] == 555


def test_close_unknown_ticket_fails_gracefully(connected_gateway: MT5Gateway):
    result = connected_gateway.close_position(999)
    assert result.success is False
