"""Domain-level exceptions, mapped to HTTP responses in app/main.py."""

from __future__ import annotations


class FathirError(Exception):
    """Base class for all application-raised errors."""

    status_code: int = 500
    default_message: str = "An unexpected error occurred."

    def __init__(self, message: str | None = None):
        super().__init__(message or self.default_message)
        self.message = message or self.default_message


class BrokerUnavailableError(FathirError):
    """Raised when the configured broker gateway cannot service a request."""

    status_code = 503
    default_message = "The broker connection is unavailable."


class BrokerConnectionError(FathirError):
    """Raised when connecting/authenticating to the broker terminal fails."""

    status_code = 502
    default_message = "Failed to connect to the broker terminal."


class SymbolNotFoundError(FathirError):
    status_code = 404
    default_message = "The requested symbol was not found."


class InsufficientDataError(FathirError):
    """Raised when there isn't enough OHLCV history to run an analysis."""

    status_code = 422
    default_message = "Not enough market data to complete this analysis."


class RiskLimitExceededError(FathirError):
    status_code = 409
    default_message = "This action would exceed a configured risk limit."


class AIProviderError(FathirError):
    status_code = 502
    default_message = "The AI provider request failed."


class NotFoundError(FathirError):
    status_code = 404
    default_message = "The requested resource was not found."


class ValidationFailedError(FathirError):
    status_code = 422
    default_message = "Validation failed."


class TelegramDeliveryError(FathirError):
    status_code = 502
    default_message = "Failed to deliver a Telegram notification."
