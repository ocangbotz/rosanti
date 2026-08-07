"""`IBrokerGateway` — the interface every broker connection implements.

See docs/ARCHITECTURE.md §3 for why this exists: `MetaTrader5` only runs on
Windows against a live terminal, so every other layer of the app (analysis,
strategies, API, frontend) is built against this interface instead, with
`MockGateway` standing in during development/tests and `MT5Gateway` used in
production on the Windows host that actually runs MT5.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd

from app.core.constants import Timeframe
from app.schemas.account import LiveAccountInfo
from app.services.broker.schemas import OrderRequest, OrderResult, PositionInfo, SymbolInfo


class IBrokerGateway(ABC):
    """Abstract broker connection. All methods are synchronous to mirror the
    underlying `MetaTrader5` SDK, which is itself synchronous/blocking;
    callers that need async should run these in a thread pool executor."""

    @abstractmethod
    def connect(self) -> None:
        """Establish (or re-establish) the connection to the broker terminal."""

    @abstractmethod
    def disconnect(self) -> None:
        """Cleanly release the connection."""

    @property
    @abstractmethod
    def is_connected(self) -> bool: ...

    @abstractmethod
    def get_ohlc(self, symbol: str, timeframe: Timeframe, count: int) -> pd.DataFrame:
        """Return OHLCV history in the standard contract defined by
        `app.analysis.ohlcv` (columns: time, open, high, low, close, volume),
        most recent candle last."""

    @abstractmethod
    def get_symbol_info(self, symbol: str) -> SymbolInfo:
        """Current spread, tick size, and contract specification for `symbol`."""

    @abstractmethod
    def get_account_info(self) -> LiveAccountInfo:
        """Live balance/equity/margin/leverage snapshot."""

    @abstractmethod
    def get_open_positions(self) -> list[PositionInfo]:
        """All currently open positions on the connected account."""

    @abstractmethod
    def place_order(self, request: OrderRequest) -> OrderResult:
        """Submit a market order."""

    @abstractmethod
    def close_position(self, ticket: int) -> OrderResult:
        """Close an open position by ticket number."""
