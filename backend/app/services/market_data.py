"""`MarketDataService` — a light caching layer over `IBrokerGateway.get_ohlc`.

Both the real MT5 terminal and the mock gateway do real work on every call
(an IPC round-trip, or regenerating a synthetic series); the dashboard and
the scheduler both poll frequently, so a short TTL cache keyed by
(symbol, timeframe, count) avoids redundant broker calls within the same
polling window without risking serving stale data across it.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd

from app.config import get_settings
from app.core.constants import Timeframe
from app.schemas.account import LiveAccountInfo
from app.services.broker.base import IBrokerGateway
from app.services.broker.schemas import OrderRequest, OrderResult, PositionInfo, SymbolInfo

DEFAULT_OHLC_COUNT = 300


class MarketDataService:
    def __init__(self, gateway: IBrokerGateway, cache_ttl_seconds: float | None = None):
        self._gateway = gateway
        self._cache_ttl = (
            cache_ttl_seconds
            if cache_ttl_seconds is not None
            else float(get_settings().market_poll_interval_seconds)
        )
        self._ohlc_cache: dict[tuple[str, Timeframe, int], tuple[datetime, pd.DataFrame]] = {}

    def _ensure_connected(self) -> None:
        if not self._gateway.is_connected:
            self._gateway.connect()

    def get_ohlc(
        self,
        symbol: str,
        timeframe: Timeframe,
        count: int = DEFAULT_OHLC_COUNT,
        *,
        use_cache: bool = True,
    ) -> pd.DataFrame:
        key = (symbol.upper(), timeframe, count)
        if use_cache and key in self._ohlc_cache:
            cached_at, cached_df = self._ohlc_cache[key]
            if (datetime.now(UTC) - cached_at).total_seconds() < self._cache_ttl:
                return cached_df.copy()

        self._ensure_connected()
        df = self._gateway.get_ohlc(symbol, timeframe, count)
        self._ohlc_cache[key] = (datetime.now(UTC), df)
        return df.copy()

    def get_symbol_info(self, symbol: str) -> SymbolInfo:
        self._ensure_connected()
        return self._gateway.get_symbol_info(symbol)

    def get_account_info(self) -> LiveAccountInfo:
        self._ensure_connected()
        return self._gateway.get_account_info()

    def get_open_positions(self) -> list[PositionInfo]:
        self._ensure_connected()
        return self._gateway.get_open_positions()

    def place_order(self, request: OrderRequest) -> OrderResult:
        self._ensure_connected()
        return self._gateway.place_order(request)

    def close_position(self, ticket: int) -> OrderResult:
        self._ensure_connected()
        return self._gateway.close_position(ticket)
