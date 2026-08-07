# Fathir AI Trading Assistant — Architecture

## 1. Design Philosophy

The assistant's single most important constraint is stated in the product brief:

> The assistant MUST NOT blindly generate Buy/Sell signals. It must analyze market
> structure, confluence, and risk, and explain WHY a trade is valid.

This drives the whole architecture. The system is split into a **deterministic
analysis pipeline** (indicators → structure → confluence → risk) that produces
verifiable, numeric, reproducible output, and a **narration layer** (the "AI"
layer) that only explains what the deterministic pipeline already decided. The
LLM is never asked "should I buy?" — it is given the computed structure/indicator
facts and asked to narrate them. This keeps every recommendation auditable: a
trader can always trace a confidence score back to the concrete rule that
produced each point.

```
 MT5 / Broker            Economic Calendar          User Upload
      │                         │                         │
      ▼                         ▼                         ▼
┌───────────┐           ┌───────────────┐         ┌───────────────┐
│  Market    │           │  News Filter   │         │  Screenshot    │
│  Data      │           │  Service       │         │  Analyzer (VLM)│
│  Service   │           └───────┬───────┘         └───────┬───────┘
└─────┬─────┘                    │                         │
      ▼                          │                         │
┌───────────────────┐            │                         │
│  Analysis Engine    │           │                         │
│  - indicators       │           │                         │
│  - market structure │           │                         │
│  - liquidity/FVG/OB │           │                         │
│  - S/R, supply/dem. │           │                         │
│  - sessions/vol.    │           │                         │
└─────────┬──────────┘            │                         │
          ▼                       │                         │
┌───────────────────┐             │                         │
│ Confluence Scorer   │            │                         │
│ (strategies/)       │            │                         │
└─────────┬──────────┘             │                         │
          ▼                        ▼                         │
┌───────────────────┐    ┌──────────────────┐                │
│ Trade Setup         │    │  Risk Engine      │               │
│ Generator            │──▶│  (position size,  │               │
│ (Entry/SL/TP/RR/     │    │  limits, BE calc) │               │
│  Confidence/Reasons) │    └──────────────────┘                │
└─────────┬───────────┘                                        │
          ▼                                                     │
┌───────────────────┐        ┌───────────────────┐             │
│  AI Narrator        │◀──────│  (feeds structured │◀────────────┘
│  (LLM explains the  │        │   facts, not raw   │
│   computed facts)    │        │   opinions)         │
└─────────┬───────────┘        └───────────────────┘
          ▼
┌────────────────────────────────────────────────────┐
│  API layer (FastAPI) → Journal, Telegram, Dashboard  │
└────────────────────────────────────────────────────┘
```

## 2. Layered Modules (SOLID)

| Layer | Responsibility | Depends on |
|---|---|---|
| `analysis/` | Pure, side-effect-free computation on OHLCV DataFrames: indicators, structure, liquidity, levels, sessions, volatility. No I/O, no broker knowledge. | pandas/numpy only |
| `strategies/` | Combines `analysis/` outputs into a confluence score and a concrete trade setup (entry/SL/TP/RR/confidence/reasons). | `analysis/` |
| `risk/` | Position sizing, daily loss limits, max trades/day, drawdown tracking, breakeven calculator. | account state only |
| `services/broker/` | `IBrokerGateway` interface + `MT5Gateway` (real) + `MockGateway` (deterministic, for dev/tests without a live terminal). | MetaTrader5 SDK (optional) |
| `services/ai/` | `ILLMProvider` interface + `AnthropicProvider`. `narrator.py` turns structured analysis into prose. `screenshot_analyzer.py` sends an uploaded chart image to a vision-capable model with a strict structured-output prompt. | httpx |
| `services/telegram/` | Bot commands + outbound notifier (trade opened/closed, SL/TP hit, news warnings, daily summary). | python-telegram-bot |
| `services/news/` | Economic calendar ingestion + high-impact event detection (NFP/CPI/FOMC/Rate decisions). | httpx |
| `journal/` | Trade journal repository (CRUD) + reporting (win rate, weekly/monthly P&L). | `database/` |
| `database/` | SQLAlchemy models + Alembic migrations. SQLite by default, Postgres via `DATABASE_URL`. | SQLAlchemy |
| `api/` | Thin FastAPI routers. No business logic — delegates to the layers above. | everything else |
| `core/` | Cross-cutting: settings, logging, credential encryption, exceptions. | - |

Dependency direction is strictly top-to-bottom in the table above — e.g.
`analysis/` never imports from `services/`, so indicator/structure logic can be
unit-tested with synthetic DataFrames and no broker connection at all.

## 3. Why an interface for the broker gateway?

`MetaTrader5` is a Windows-only C-extension that requires a running MT5
terminal. This container/CI environment cannot run it. Building directly
against the `MetaTrader5` module would make the rest of the system untestable.
Instead:

- `IBrokerGateway` (abstract base class) defines `connect`, `get_ohlc`,
  `get_symbol_info` (spread, leverage), `get_account_info` (balance, equity,
  margin), `get_open_positions`, `place_order`, `close_position`.
- `MT5Gateway` implements it for real using the `MetaTrader5` package,
  imported lazily so the module still loads on Linux/macOS dev machines; it
  raises a clear `BrokerUnavailableError` if the SDK/terminal isn't present.
- `MockGateway` implements it with deterministic synthetic OHLCV generation
  and an in-memory account/position book, so the entire API surface,
  analysis pipeline, and frontend can be developed/tested without Windows.

Which implementation is active is chosen by `settings.BROKER_MODE`
(`mt5` | `mock`), read from `.env`.

## 4. Data flow for "Smart Trade Setup"

1. `MarketDataService` pulls OHLCV via the active `IBrokerGateway`.
2. `analysis/indicators.py` computes EMA(20/50/200), RSI(14), MACD(12/26/9),
   ATR(14), volume metrics.
3. `analysis/structure.py` computes swing highs/lows, trend direction, BOS
   and CHOCH events.
4. `analysis/liquidity.py` detects liquidity sweeps, order blocks, and Fair
   Value Gaps.
5. `analysis/levels.py` derives support/resistance and supply/demand zones.
6. `analysis/sessions.py` / `volatility.py` tag the current session (Asia/
   London/New York) and volatility regime (ATR percentile).
7. `strategies/confluence.py` scores every one of the above signals with a
   weighted rule table, producing a 0–100 confidence score and a list of
   `Reason` objects (`factor`, `direction`, `weight`, `description`).
8. `strategies/setup_generator.py` turns the highest-confidence bias into a
   concrete `TradeSetup` (entry, stop loss placed beyond the invalidation
   structure, take-profit at the next opposing liquidity/level, RR ratio).
9. `risk/position_sizing.py` converts the setup + account risk % into a lot
   size.
10. `services/ai/narrator.py` sends the structured `TradeSetup` + `Reason[]`
    to the LLM to produce the natural-language paragraph — the LLM is
    instructed to summarize only, never to alter the numbers.

## 5. Persistence

SQLAlchemy 2.0 declarative models, Alembic migrations, SQLite file by
default (`sqlite:///./data/fathir.db`), swappable to Postgres by changing
`DATABASE_URL` — no code changes required since no SQLite-specific SQL is
used.

Core tables: `accounts`, `trade_setups`, `journal_entries`, `journal_screenshots`,
`risk_settings`, `news_events`, `telegram_subscribers`, `app_settings`.

## 6. API & Realtime

FastAPI REST endpoints for CRUD/analysis, plus a WebSocket (`/ws/market`)
that pushes live price/analysis updates to the dashboard so charts update
without polling.

## 7. Security

- All secrets (broker password, Telegram token, LLM API key) live in `.env`,
  never committed (`.env.example` documents the shape).
- Broker credentials stored in the DB (if persisted for convenience) are
  encrypted at rest with Fernet (`core/security.py`), key from
  `CREDENTIAL_ENCRYPTION_KEY`.
- Structured logging (`core/logging_config.py`) with request IDs; no secrets
  ever logged.
- Pydantic validates every request payload; upload endpoints restrict file
  type/size for screenshots.
- Dashboard API protected by a single-user API key (`X-API-Key` header) —
  this is a personal trading tool, not a multi-tenant SaaS, so full OAuth is
  intentionally out of scope, but the dependency is isolated in
  `api/deps.py` so it can be swapped later.

## 8. Frontend

React + TypeScript + Vite + TailwindCSS, dark-mode-first fintech UI (inspired
by TradingView/Binance/Notion). `lightweight-charts` (TradingView's own OSS
charting library) renders candlesticks + overlays (EMAs, S/R zones, order
blocks, FVGs) using the same structure data the backend computed — so the
chart draws exactly what the AI reasoned about, not a separate
re-interpretation.

## 9. Deployment

Docker Compose with three services: `backend` (uvicorn), `frontend` (nginx
serving the Vite build), and a shared `data/` volume for SQLite +
screenshots. Swapping to Postgres adds a fourth `db` service and a
`DATABASE_URL` change only.
