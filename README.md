# Fathir AI Trading Assistant

An AI-assisted market analysis and trade-setup engine for professional traders.

**It does not generate blind buy/sell signals.** Every trade idea flows through a
deterministic pipeline — indicators → market structure → confluence scoring → risk —
before an LLM ever touches it, and the LLM is only allowed to *narrate* the facts
that pipeline already computed. Every confidence score ships with the named reasons
behind it. See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full design
rationale.

## Features

- **MT5 integration** — real broker connection (Windows) or a fully-functional mock
  broker (deterministic synthetic market) for development, behind a shared
  `IBrokerGateway` interface
- **Market analysis** — trend, support/resistance, supply/demand, Break of Structure
  (BOS), Change of Character (CHOCH), liquidity sweeps, order blocks, Fair Value
  Gaps, EMA/RSI/MACD/ATR, volume, trading session, volatility regime
- **Smart Trade Setup** — entry, stop loss, take profit, risk/reward, a 0–100
  confidence score, and the itemized confluence reasons behind it
- **AI narration** — a natural-language summary of the computed facts, and a
  vision-based screenshot analyzer for uploaded chart images
- **Risk management** — lot size calculator, breakeven calculator, daily loss
  limit, max trades/day, drawdown tracking
- **Trading journal** — full CRUD, win rate, weekly/monthly reports
- **Dashboard** — dark-first fintech UI (React + Tailwind), TradingView-style
  candlestick chart with a live WebSocket price/structure stream
- **Telegram bot** — `/status`, `/positions`, `/analyze`, `/journal`, plus
  proactive alerts (trade opened/closed, SL/TP hit, new setup, high-impact news,
  daily summary)
- **Economic calendar** — high-impact event detection (NFP, CPI, FOMC, rate
  decisions) with a pre-trade warning window

## Tech stack

| Layer | Choice |
|---|---|
| Backend | Python 3.11, FastAPI, SQLAlchemy 2.0, Alembic, Pandas/NumPy |
| Broker | `MetaTrader5` SDK (Windows) or a built-in mock gateway |
| AI | Anthropic Claude (text + vision), via a swappable `ILLMProvider` interface |
| Database | SQLite by default, Postgres via one `DATABASE_URL` change |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, `lightweight-charts`, Recharts |
| Messaging | `python-telegram-bot` |
| Deployment | Docker + Docker Compose |

## Quick start

### Docker Compose (recommended)

```bash
cp backend/.env.example backend/.env   # fill in as needed — defaults run in mock mode
docker compose up --build
```

- Frontend: http://localhost
- Backend API + docs: http://localhost:8000/docs

### Manual (local development)

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 — the Vite dev server proxies `/api` and `/ws` to
`localhost:8000` automatically (see `frontend/vite.config.ts`).

Everything above runs out of the box in **mock broker mode** — no MetaTrader5
terminal, Telegram bot, or Anthropic API key required. See
[`docs/SETUP.md`](docs/SETUP.md) to connect a real MT5 account, enable the
Telegram bot, and turn on AI narration/screenshot analysis.

## Documentation

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — system design and the
  "explain WHY" pipeline
- [`docs/ROADMAP.md`](docs/ROADMAP.md) — the milestone-by-milestone build plan
- [`docs/SETUP.md`](docs/SETUP.md) — full setup, configuration, and deployment guide
- [`docs/API.md`](docs/API.md) — REST/WebSocket API reference

## Testing

```bash
# Backend — 188 tests, 90%+ coverage
cd backend && source .venv/bin/activate
pytest
ruff check app tests && black --check app tests && mypy app

# Frontend
cd frontend
npm run typecheck
npm run lint
```

## Project structure

```
backend/    FastAPI app: analysis, strategies, risk, journal, services (broker/ai/
            telegram/news), api routers, database models, Alembic migrations, tests
frontend/   React + TypeScript dashboard: pages, components, api client, store
docs/       Architecture, roadmap, setup guide, API reference
docker-compose.yml, backend/Dockerfile, frontend/Dockerfile
```

## License

Proprietary — all rights reserved unless a license file states otherwise.
