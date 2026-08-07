"""
FastAPI application entrypoint.

Router wiring happens incrementally as each domain module is built (see
docs/ROADMAP.md milestone 11); this file is extended, not rewritten, as
routers land.
"""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import __version__
from app.api.routers import account, analysis, journal, market, news, risk, screenshot, setups, ws
from app.api.routers import settings as settings_router
from app.api.routers import telegram as telegram_router
from app.config import get_settings
from app.core.exceptions import FathirError
from app.core.logging_config import configure_logging, get_logger, request_id_ctx
from app.database.base import Base
from app.database.session import engine
from app.services.scheduler import TradingScheduler
from app.services.telegram.bot import build_application

settings = get_settings()
configure_logging(settings.log_level)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.is_sqlite:
        # Convenience for local/dev use: SQLite files are created on first run.
        # Production/Postgres deployments should run `alembic upgrade head`.
        Base.metadata.create_all(bind=engine)
        logger.info("SQLite schema ensured at startup.")
    logger.info("%s v%s starting in %s mode.", settings.app_name, __version__, settings.environment)

    scheduler = TradingScheduler(settings)
    scheduler.start()

    telegram_application = None
    if settings.telegram_enabled and settings.telegram_bot_token:
        try:
            telegram_application = build_application(settings)
            assert telegram_application.updater is not None  # always set by ApplicationBuilder
            await telegram_application.initialize()
            await telegram_application.start()
            await telegram_application.updater.start_polling()
            logger.info("Telegram bot polling started.")
        except FathirError as exc:
            logger.warning("Telegram bot not started: %s", exc.message)
            telegram_application = None

    yield

    if telegram_application is not None:
        assert telegram_application.updater is not None
        await telegram_application.updater.stop()
        await telegram_application.stop()
        await telegram_application.shutdown()
    scheduler.shutdown()
    logger.info("%s shutting down.", settings.app_name)


app = FastAPI(
    title=settings.app_name,
    version=__version__,
    description=(
        "AI-assisted market analysis and trade-setup engine. Explains WHY a "
        "trade is valid via deterministic structure/confluence analysis; "
        "never emits blind buy/sell signals."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    token = request_id_ctx.set(request_id)
    try:
        response = await call_next(request)
    finally:
        request_id_ctx.reset(token)
    response.headers["X-Request-ID"] = request_id
    return response


@app.exception_handler(FathirError)
async def fathir_error_handler(request: Request, exc: FathirError) -> JSONResponse:
    logger.warning("Handled error on %s %s: %s", request.method, request.url.path, exc.message)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


API_PREFIX = "/api/v1"

app.include_router(account.router, prefix=API_PREFIX)
app.include_router(market.router, prefix=API_PREFIX)
app.include_router(analysis.router, prefix=API_PREFIX)
app.include_router(setups.router, prefix=API_PREFIX)
app.include_router(risk.router, prefix=API_PREFIX)
app.include_router(journal.router, prefix=API_PREFIX)
app.include_router(news.router, prefix=API_PREFIX)
app.include_router(telegram_router.router, prefix=API_PREFIX)
app.include_router(screenshot.router, prefix=API_PREFIX)
app.include_router(settings_router.router, prefix=API_PREFIX)
app.include_router(ws.router)  # WebSocket route, no versioned prefix or API-key gate


@app.get("/health", tags=["system"])
async def health_check() -> dict:
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": __version__,
        "environment": settings.environment,
        "broker_mode": settings.broker_mode,
    }


@app.get("/", tags=["system"], status_code=status.HTTP_200_OK)
async def root() -> dict:
    return {"message": f"{settings.app_name} API — see /docs for the interactive API reference."}
