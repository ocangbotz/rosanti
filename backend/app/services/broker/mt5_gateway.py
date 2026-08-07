"""Real MetaTrader 5 broker gateway.

The `MetaTrader5` package is a Windows-only C-extension that talks to a
locally running MT5 terminal over IPC — it cannot be installed or imported
on Linux/macOS, so it is imported lazily inside `connect()` rather than at
module load time. This lets the rest of the backend (and this file itself)
be imported freely in CI/dev containers; the import only fails at the
moment someone actually tries to use `BROKER_MODE=mt5` without a real
Windows+MT5 environment, with a clear `BrokerUnavailableError` explaining
why.
"""

from __future__ import annotations

from datetime import UTC
from types import ModuleType
from typing import Any

import pandas as pd

from app.config import Settings
from app.core.constants import Timeframe, TradeDirection
from app.core.exceptions import BrokerConnectionError, BrokerUnavailableError, SymbolNotFoundError
from app.schemas.account import LiveAccountInfo
from app.services.broker.base import IBrokerGateway
from app.services.broker.schemas import OrderRequest, OrderResult, PositionInfo, SymbolInfo


def _import_mt5() -> ModuleType:
    try:
        import MetaTrader5 as mt5
    except ImportError as exc:
        raise BrokerUnavailableError(
            "The MetaTrader5 package is not installed/importable. It only runs on "
            "Windows against a live MT5 terminal — install it there with "
            "`pip install MetaTrader5` and set BROKER_MODE=mt5, or use "
            "BROKER_MODE=mock for development."
        ) from exc
    return mt5


class MT5Gateway(IBrokerGateway):
    def __init__(self, settings: Settings):
        self._settings = settings
        self._mt5: ModuleType | None = None
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    def connect(self) -> None:
        mt5 = _import_mt5()
        self._mt5 = mt5

        kwargs: dict[str, Any] = {"timeout": self._settings.mt5_timeout_ms}
        if self._settings.mt5_terminal_path:
            kwargs["path"] = self._settings.mt5_terminal_path
        if self._settings.mt5_login:
            kwargs["login"] = self._settings.mt5_login
        if self._settings.mt5_password:
            kwargs["password"] = self._settings.mt5_password
        if self._settings.mt5_server:
            kwargs["server"] = self._settings.mt5_server

        if not mt5.initialize(**kwargs):
            code, message = mt5.last_error()
            raise BrokerConnectionError(f"MT5 initialize() failed ({code}): {message}")

        self._connected = True

    def disconnect(self) -> None:
        if self._mt5 is not None and self._connected:
            self._mt5.shutdown()
        self._connected = False

    def _require_connection(self) -> ModuleType:
        if not self._connected or self._mt5 is None:
            raise BrokerUnavailableError("MT5 gateway is not connected. Call connect() first.")
        return self._mt5

    _TIMEFRAME_MAP_NAMES: dict[Timeframe, str] = {
        Timeframe.M1: "TIMEFRAME_M1",
        Timeframe.M5: "TIMEFRAME_M5",
        Timeframe.M15: "TIMEFRAME_M15",
        Timeframe.M30: "TIMEFRAME_M30",
        Timeframe.H1: "TIMEFRAME_H1",
        Timeframe.H4: "TIMEFRAME_H4",
        Timeframe.D1: "TIMEFRAME_D1",
        Timeframe.W1: "TIMEFRAME_W1",
    }

    def get_ohlc(self, symbol: str, timeframe: Timeframe, count: int) -> pd.DataFrame:
        mt5 = self._require_connection()
        mt5_timeframe = getattr(mt5, self._TIMEFRAME_MAP_NAMES[timeframe])

        rates = mt5.copy_rates_from_pos(symbol, mt5_timeframe, 0, count)
        if rates is None or len(rates) == 0:
            code, message = mt5.last_error()
            raise SymbolNotFoundError(
                f"No OHLC data returned for {symbol!r} ({timeframe.value}): [{code}] {message}"
            )

        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
        df = df.rename(columns={"tick_volume": "volume"})
        return df[["time", "open", "high", "low", "close", "volume"]]

    def get_symbol_info(self, symbol: str) -> SymbolInfo:
        mt5 = self._require_connection()
        info = mt5.symbol_info(symbol)
        tick = mt5.symbol_info_tick(symbol)
        if info is None or tick is None:
            raise SymbolNotFoundError(f"Symbol {symbol!r} is not available from this broker.")

        pip_size = info.point * 10 if info.digits in (3, 5) else info.point
        pip_value_per_lot = self._calc_pip_value(mt5, symbol, pip_size, tick.ask)

        return SymbolInfo(
            symbol=symbol,
            bid=tick.bid,
            ask=tick.ask,
            spread_points=info.spread,
            point=info.point,
            digits=info.digits,
            contract_size=info.trade_contract_size,
            volume_min=info.volume_min,
            volume_max=info.volume_max,
            volume_step=info.volume_step,
            pip_size=pip_size,
            pip_value_per_lot=pip_value_per_lot,
        )

    def _calc_pip_value(self, mt5: ModuleType, symbol: str, pip_size: float, price: float) -> float:
        """Value in account currency of a 1-pip move at 1.0 lot, using MT5's
        own `order_calc_profit` for accuracy (handles cross-currency pairs
        correctly, unlike a flat contract-size approximation)."""
        try:
            profit = mt5.order_calc_profit(mt5.ORDER_TYPE_BUY, symbol, 1.0, price, price + pip_size)
            if profit is not None and profit > 0:
                return float(profit)
        except Exception:  # pragma: no cover - defensive: broker-specific quirks
            pass
        # Fallback approximation if order_calc_profit is unavailable.
        info = mt5.symbol_info(symbol)
        return float(info.trade_contract_size * pip_size) if info else 10.0

    def get_account_info(self) -> LiveAccountInfo:
        mt5 = self._require_connection()
        account = mt5.account_info()
        if account is None:
            raise BrokerConnectionError(
                "Failed to read MT5 account info — is the terminal logged in?"
            )

        return LiveAccountInfo(
            login=account.login,
            server=account.server,
            currency=account.currency,
            leverage=account.leverage,
            balance=account.balance,
            equity=account.equity,
            margin=account.margin,
            free_margin=account.margin_free,
            margin_level=account.margin_level if account.margin_level else None,
            profit=account.profit,
            connected=True,
        )

    def get_open_positions(self) -> list[PositionInfo]:
        mt5 = self._require_connection()
        positions = mt5.positions_get()
        if positions is None:
            return []

        results = []
        for pos in positions:
            direction = TradeDirection.BUY if pos.type == 0 else TradeDirection.SELL
            results.append(
                PositionInfo(
                    ticket=pos.ticket,
                    symbol=pos.symbol,
                    direction=direction,
                    volume=pos.volume,
                    open_price=pos.price_open,
                    current_price=pos.price_current,
                    stop_loss=pos.sl or None,
                    take_profit=pos.tp or None,
                    profit=pos.profit,
                    swap=pos.swap,
                    opened_at=pd.Timestamp(pos.time, unit="s", tz=UTC).to_pydatetime(),
                )
            )
        return results

    def place_order(self, request: OrderRequest) -> OrderResult:
        mt5 = self._require_connection()
        tick = mt5.symbol_info_tick(request.symbol)
        if tick is None:
            raise SymbolNotFoundError(
                f"Symbol {request.symbol!r} is not available from this broker."
            )

        order_type = (
            mt5.ORDER_TYPE_BUY if request.direction == TradeDirection.BUY else mt5.ORDER_TYPE_SELL
        )
        price = tick.ask if request.direction == TradeDirection.BUY else tick.bid

        mt5_request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": request.symbol,
            "volume": request.volume,
            "type": order_type,
            "price": price,
            "sl": request.stop_loss or 0.0,
            "tp": request.take_profit or 0.0,
            "deviation": 20,
            "magic": 574821,
            "comment": request.comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        result = mt5.order_send(mt5_request)

        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            message = result.comment if result is not None else "order_send returned None"
            return OrderResult(success=False, message=message)

        return OrderResult(
            success=True, ticket=result.order, executed_price=result.price, message="OK"
        )

    def close_position(self, ticket: int) -> OrderResult:
        mt5 = self._require_connection()
        positions = mt5.positions_get(ticket=ticket)
        if not positions:
            return OrderResult(
                success=False, message=f"No open position found for ticket {ticket}."
            )

        position = positions[0]
        tick = mt5.symbol_info_tick(position.symbol)
        if tick is None:
            raise SymbolNotFoundError(
                f"Symbol {position.symbol!r} is not available from this broker."
            )

        is_buy_position = position.type == 0
        close_type = mt5.ORDER_TYPE_SELL if is_buy_position else mt5.ORDER_TYPE_BUY
        price = tick.bid if is_buy_position else tick.ask

        mt5_request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": position.symbol,
            "volume": position.volume,
            "type": close_type,
            "position": ticket,
            "price": price,
            "deviation": 20,
            "magic": 574821,
            "comment": "Fathir AI Trading Assistant close",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        result = mt5.order_send(mt5_request)

        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            message = result.comment if result is not None else "order_send returned None"
            return OrderResult(success=False, message=message)

        return OrderResult(
            success=True, ticket=result.order, executed_price=result.price, message="OK"
        )
