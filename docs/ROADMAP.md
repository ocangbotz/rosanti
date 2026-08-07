# Implementation Roadmap

Work is split into milestones. Each milestone is committed separately, and
backend milestones are followed by `ruff`/`pytest` before moving on, per the
project's Claude Code Mode rules.

| # | Milestone | Contents |
|---|---|---|
| 0 | Scaffolding | `.gitignore`, `docs/ARCHITECTURE.md`, `docs/ROADMAP.md`, folder skeleton |
| 1 | Backend core | `pyproject`/requirements, settings, logging, security (Fernet), exceptions, DB base + session + Alembic, FastAPI app skeleton + health check |
| 2 | Database models & schemas | SQLAlchemy models (accounts, trade_setups, journal, risk_settings, news_events, telegram_subscribers, app_settings) + Pydantic schemas + first Alembic migration |
| 3 | Analysis engine | `indicators.py` (EMA/RSI/MACD/ATR/volume), `structure.py` (swings, trend, BOS/CHOCH), `liquidity.py` (sweeps, order blocks, FVG), `levels.py` (S/R, supply/demand), `sessions.py`, `volatility.py` + unit tests on synthetic OHLCV |
| 4 | Strategy engine | `confluence.py` scorer, `setup_generator.py` (entry/SL/TP/RR/confidence/reasons) + unit tests |
| 5 | Risk management | position sizing, daily loss limit, max trades/day, drawdown tracker, breakeven calculator + unit tests |
| 6 | Broker integration | `IBrokerGateway`, `MT5Gateway` (real MetaTrader5 SDK, lazy import), `MockGateway` (deterministic synthetic data), `MarketDataService` |
| 7 | AI modules | `ILLMProvider`, `AnthropicProvider`, `narrator.py` (chart-to-prose), `screenshot_analyzer.py` (vision-based chart image report) |
| 8 | Journal | repository (CRUD + screenshot storage), reports (win rate, weekly/monthly P&L) |
| 9 | News filter | economic calendar client, high-impact event classifier (NFP/CPI/FOMC/rate decisions), pre-trade warning |
| 10 | Telegram bot | bot commands (`/status`, `/analyze`, `/positions`, `/journal`), notifier (trade opened/closed, SL/TP hit, news warning, daily summary), background scheduler |
| 11 | API layer | routers for market/analysis/setups/risk/journal/account/news/telegram/screenshot/settings, WebSocket for live updates, wire into `main.py` |
| 12 | Backend tests + lint pass | full `pytest` + `ruff check` + `black --check`, fix all issues |
| 13 | Frontend scaffold | Vite + React + TS + Tailwind, dark theme tokens, routing, layout shell (sidebar/topbar), API client, state store |
| 14 | Frontend pages | Dashboard, Market (chart), Analysis, Journal, Performance, Settings, Telegram — fully wired to backend endpoints |
| 15 | Docker & compose | backend Dockerfile, frontend Dockerfile (nginx), `docker-compose.yml`, `.env.example` |
| 16 | Documentation | root `README.md`, `docs/SETUP.md`, `docs/API.md`, final review |

Milestones 0–12 (backend) are executed first end-to-end since the frontend
depends on the API contracts being stable. Frontend milestones consume the
same `schemas/` shapes documented in `docs/API.md`.
