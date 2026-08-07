"""Generic WebSocket connection registry, used for broadcast-style pushes
(kept separate from the market-data streaming loop in `market_stream.py`,
which is a per-connection pull loop rather than a broadcast)."""

from __future__ import annotations

from fastapi import WebSocket

from app.core.logging_config import get_logger

logger = get_logger(__name__)


class ConnectionManager:
    def __init__(self) -> None:
        self._active: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._active.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self._active.discard(websocket)

    async def broadcast(self, message: dict) -> None:
        for websocket in list(self._active):
            try:
                await websocket.send_json(message)
            except Exception as exc:  # noqa: BLE001 -- a dead socket must not break the broadcast
                logger.warning("Dropping WebSocket connection after send failure: %s", exc)
                self.disconnect(websocket)

    @property
    def connection_count(self) -> int:
        return len(self._active)
