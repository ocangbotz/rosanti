"""Deterministic mock broker gateway.

Used whenever `BROKER_MODE=mock` (the default), which is every environment
without a live Windows MT5 terminal: local dev, CI, and this container.
Generates a plausible, seeded synthetic market (trend cycles, realistic
spread) and a fully functional in-memory account/position book, so the
entire API surface — including placing and closing trades — works
end-to-end without a real broker.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta

import numpy as np
import pandas as pd

from app.config import Settings
from app.core.constants import Timeframe, TradeDirection
from app.schemas.account import LiveAccountInfo
from app.services.broker.base import IBrokerGateway
from app.services.broker.schemas import OrderRequest, OrderResult, PositionInfo, SymbolInfo

_BASE_PRICES: dict[str, float] = {
    "EURUSD": 1.0850,
    "GBPUSD": 1.2650,
    "USDJPY": 151.20,
    "USDCHF": 0.9050,
    "AUDUSD": 0.6550,
    "USDCAD": 1.3650,
    "NZDUSD": 0.6050,
    "XAUUSD": 2330.00,
    "BTCUSD": 62000.00,
}

_STANDARD_CONTRACT_SIZE = 100_000.0


def _symbol_precision(symbol: str) -> tuple[int, float, float]:
    """Returns (digits, point, pip_size) for a symbol, matching typical
    broker conventions: 3-digit JPY pairs, 5-digit everything else, with
    gold/crypto using coarser precision."""
    if symbol.upper().endswith("JPY"):
        return 3, 0.001, 0.01
    if symbol.upper().startswith("XAU"):
        return 2, 0.01, 0.1
    if "BTC" in symbol.upper():
        return 2, 0.01, 1.0
    return 5, 0.00001, 0.0001


class MockGateway(IBrokerGateway):
    def __init__(self, settings: Settings):
        self._settings = settings
        self._connected = False
        self._balance = 10_000.0
        self._leverage = 100
        self._currency = "USD"
        self._login = 90_00001
        self._server = "Fathir-Mock-Server"
        self._positions: dict[int, dict] = {}
        self._next_ticket = 1_000_001

    @property
    def is_connected(self) -> bool:
        return self._connected

    def connect(self) -> None:
        self._connected = True

    def disconnect(self) -> None:
        self._connected = False

    def _base_price(self, symbol: str) -> float:
        if symbol.upper() in _BASE_PRICES:
            return _BASE_PRICES[symbol.upper()]
        # Deterministic pseudo-price for unrecognized symbols, so every
        # symbol string still produces a stable, plausible market.
        seed = sum(ord(c) for c in symbol.upper())
        return 1.0 + (seed % 500) / 100.0

    def _generate_series(
        self, symbol: str, timeframe: Timeframe, count: int, end_time: datetime | None = None
    ) -> pd.DataFrame:
        """Deterministic synthetic OHLCV ending at `end_time` (default now).

        Seeded from the symbol name so the same symbol always produces the
        same *shape* of history, while a slow sine-wave drift plus noise
        gives structure/BOS/CHOCH detection real swings to find (a pure
        random walk tends to look choppy with no clean trend legs).
        """
        end_time = end_time or datetime.now(UTC)
        seed = abs(hash(symbol.upper())) % (2**32)
        rng = np.random.default_rng(seed)

        base_price = self._base_price(symbol)
        _, _, pip_size = _symbol_precision(symbol)
        noise_scale = pip_size * 3
        cycle_length = 80

        closes = [base_price]
        for i in range(1, count):
            cycle_drift = math.sin(i / cycle_length * 2 * math.pi) * pip_size * 0.8
            noise = rng.normal(0, noise_scale)
            closes.append(closes[-1] + cycle_drift + noise)
        closes_arr = np.array(closes)

        opens = np.empty(count)
        opens[0] = base_price
        opens[1:] = closes_arr[:-1]

        wick_noise = np.abs(rng.normal(0, noise_scale * 1.3, size=count))
        highs = np.maximum(opens, closes_arr) + wick_noise
        lows = np.minimum(opens, closes_arr) - wick_noise
        lows = np.maximum(lows, pip_size)  # keep prices positive

        base_volume = 1000.0
        volumes = np.abs(base_volume + rng.normal(0, base_volume * 0.2, size=count))

        step = timedelta(minutes=timeframe.minutes)
        times = [end_time - step * (count - 1 - i) for i in range(count)]

        return pd.DataFrame(
            {
                "time": times,
                "open": opens,
                "high": highs,
                "low": lows,
                "close": closes_arr,
                "volume": volumes,
            }
        )

    def get_ohlc(self, symbol: str, timeframe: Timeframe, count: int) -> pd.DataFrame:
        return self._generate_series(symbol, timeframe, count)

    def _current_price(self, symbol: str) -> float:
        series = self._generate_series(symbol, Timeframe.M1, 2)
        return float(series["close"].iloc[-1])

    def get_symbol_info(self, symbol: str) -> SymbolInfo:
        digits, point, pip_size = _symbol_precision(symbol)
        mid = self._current_price(symbol)
        half_spread = pip_size * 0.6
        bid, ask = mid - half_spread, mid + half_spread

        return SymbolInfo(
            symbol=symbol.upper(),
            bid=round(bid, digits),
            ask=round(ask, digits),
            spread_points=max(int(round((ask - bid) / point)), 1),
            point=point,
            digits=digits,
            contract_size=_STANDARD_CONTRACT_SIZE,
            volume_min=0.01,
            volume_max=100.0,
            volume_step=0.01,
            pip_size=pip_size,
            pip_value_per_lot=round(_STANDARD_CONTRACT_SIZE * pip_size, 2),
        )

    def get_account_info(self) -> LiveAccountInfo:
        floating_profit = sum(self._position_profit(p) for p in self._positions.values())
        equity = self._balance + floating_profit
        margin = sum(
            (p["volume"] * _STANDARD_CONTRACT_SIZE) / self._leverage
            for p in self._positions.values()
        )
        free_margin = equity - margin
        margin_level = (equity / margin * 100) if margin > 0 else None

        return LiveAccountInfo(
            login=self._login,
            server=self._server,
            currency=self._currency,
            leverage=self._leverage,
            balance=round(self._balance, 2),
            equity=round(equity, 2),
            margin=round(margin, 2),
            free_margin=round(free_margin, 2),
            margin_level=round(margin_level, 2) if margin_level is not None else None,
            profit=round(floating_profit, 2),
            connected=self._connected,
        )

    def _position_profit(self, position: dict) -> float:
        current_price = self._current_price(position["symbol"])
        direction_sign = 1 if position["direction"] == TradeDirection.BUY else -1
        price_diff = (current_price - position["open_price"]) * direction_sign
        return price_diff * position["volume"] * _STANDARD_CONTRACT_SIZE

    def get_open_positions(self) -> list[PositionInfo]:
        results = []
        for ticket, position in self._positions.items():
            results.append(
                PositionInfo(
                    ticket=ticket,
                    symbol=position["symbol"],
                    direction=position["direction"],
                    volume=position["volume"],
                    open_price=position["open_price"],
                    current_price=self._current_price(position["symbol"]),
                    stop_loss=position.get("stop_loss"),
                    take_profit=position.get("take_profit"),
                    profit=round(self._position_profit(position), 2),
                    swap=0.0,
                    opened_at=position["opened_at"],
                )
            )
        return results

    def place_order(self, request: OrderRequest) -> OrderResult:
        if request.volume <= 0:
            return OrderResult(success=False, message="Volume must be positive.")

        info = self.get_symbol_info(request.symbol)
        price = info.ask if request.direction == TradeDirection.BUY else info.bid

        ticket = self._next_ticket
        self._next_ticket += 1
        self._positions[ticket] = {
            "symbol": request.symbol.upper(),
            "direction": request.direction,
            "volume": request.volume,
            "open_price": price,
            "stop_loss": request.stop_loss,
            "take_profit": request.take_profit,
            "opened_at": datetime.now(UTC),
        }
        return OrderResult(
            success=True, ticket=ticket, executed_price=price, message="OK (mock fill)"
        )

    def close_position(self, ticket: int) -> OrderResult:
        position = self._positions.get(ticket)
        if position is None:
            return OrderResult(
                success=False, message=f"No open position found for ticket {ticket}."
            )

        realized_pnl = self._position_profit(position)
        self._balance += realized_pnl
        close_price = self._current_price(position["symbol"])
        del self._positions[ticket]

        return OrderResult(
            success=True, ticket=ticket, executed_price=close_price, message="OK (mock close)"
        )
