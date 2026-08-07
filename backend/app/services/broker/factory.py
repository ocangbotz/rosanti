"""Selects the active `IBrokerGateway` implementation based on `Settings.broker_mode`."""

from __future__ import annotations

from functools import lru_cache

from app.config import Settings, get_settings
from app.services.broker.base import IBrokerGateway
from app.services.broker.mock_gateway import MockGateway
from app.services.broker.mt5_gateway import MT5Gateway


def create_broker_gateway(settings: Settings | None = None) -> IBrokerGateway:
    """Construct a fresh, unconnected gateway instance for the configured mode."""
    settings = settings or get_settings()
    if settings.broker_mode == "mt5":
        return MT5Gateway(settings)
    return MockGateway(settings)


@lru_cache
def get_broker_gateway() -> IBrokerGateway:
    """Process-wide singleton gateway (connected lazily on first use).

    A singleton is appropriate here: `MockGateway` holds the in-memory
    account/position book that must persist across requests, and
    `MT5Gateway` wraps a single stateful terminal connection — neither
    should be recreated per request.
    """
    gateway = create_broker_gateway()
    gateway.connect()
    return gateway
