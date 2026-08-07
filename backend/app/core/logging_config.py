"""
Structured logging configuration.

Emits JSON logs (easy to ship to any log aggregator) with a request-id
field so a single API call can be traced across the analysis pipeline,
broker calls, and background jobs. Secrets (API keys, broker passwords,
Telegram tokens) are never logged — callers must pass already-redacted
values into log statements.
"""

from __future__ import annotations

import logging
import sys
from contextvars import ContextVar

from pythonjsonlogger import jsonlogger

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")


class RequestIdFilter(logging.Filter):
    """Injects the current request id (if any) into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx.get()
        return True


def configure_logging(level: str = "INFO") -> None:
    """Configure root logging handlers. Safe to call multiple times."""
    root_logger = logging.getLogger()
    root_logger.setLevel(level.upper())

    # Avoid duplicate handlers on reload (uvicorn --reload re-imports modules).
    root_logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    formatter = jsonlogger.JsonFormatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(request_id)s %(message)s",
        rename_fields={"asctime": "timestamp", "levelname": "level"},
    )
    handler.setFormatter(formatter)
    handler.addFilter(RequestIdFilter())
    root_logger.addHandler(handler)

    # Quiet down noisy third-party loggers.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
