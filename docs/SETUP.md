# Setup Guide

## Prerequisites

- Python 3.11+
- Node.js 20+ (22 recommended) and npm
- Docker + Docker Compose (optional, for containerized deployment)
- A MetaTrader 5 terminal on **Windows** (optional — only needed for a live
  broker connection; everything works in mock mode without it)
- An Anthropic API key (optional — only needed for AI narration and
  screenshot analysis)
- A Telegram bot token from [@BotFather](https://t.me/BotFather) (optional —
  only needed for Telegram alerts)

## 1. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` as needed (see the annotated defaults in `.env.example`; every
field is documented there). At minimum, for local development, the defaults
work as-is: `BROKER_MODE=mock`, SQLite, no API keys.

Apply the database schema:

```bash
alembic upgrade head
```

No separate seed step is needed — there's deliberately no seed script.
Rows that would normally be "seeded" (global risk settings, per-account
settings) are instead created lazily on first access, populated from the
`DEFAULT_*` values in `.env` (see `app/risk/limits.py::get_risk_settings`).
Everything else (broker accounts, journal entries, trade setups, Telegram
subscribers) is meant to start empty and fill in through normal use.

Run the API:

```bash
uvicorn app.main:app --reload
```

- Interactive API docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health

Run the test suite:

```bash
pytest                                    # 188 tests
pytest --cov=app --cov-report=term-missing  # with coverage
ruff check app tests                      # lint
black --check app tests                   # format check
mypy app                                  # type check
```

### Generating a credential encryption key

Only needed if you plan to save broker credentials via the dashboard's
"Add account" form (as opposed to authenticating purely from `.env`):

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Put the result in `CREDENTIAL_ENCRYPTION_KEY` in `.env`.

## 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. In development, Vite proxies `/api/*` and `/ws/*`
to `http://localhost:8000` (see `vite.config.ts`) — no CORS configuration or
`.env` needed for local use against a backend on the default port.

Other commands:

```bash
npm run build       # production build to dist/
npm run typecheck    # tsc -b --noEmit
npm run lint          # eslint
```

To point the dev server at a backend on a different host/port, or to build
for a deployment where the frontend and backend aren't served from the same
origin, copy `.env.example` to `.env.local` and set `VITE_API_BASE_URL` /
`VITE_WS_BASE_URL`.

## 3. Docker Compose

```bash
cp backend/.env.example backend/.env
docker compose up --build
```

- Frontend (nginx, proxies `/api` and `/ws` to the backend container):
  http://localhost
- Backend directly: http://localhost:8000

Data (SQLite database + uploaded screenshots) persists in the `backend_data`
named volume across restarts. To reset everything:

```bash
docker compose down -v
```

### Upgrading to Postgres

No application code changes are required — only `DATABASE_URL`:

1. In `backend/requirements.txt`, uncomment `psycopg2-binary`.
2. In `backend/.env`, set
   `DATABASE_URL=postgresql+psycopg2://fathir:fathir@db:5432/fathir`.
3. Start the optional `db` service alongside the rest:
   ```bash
   docker compose --profile postgres up --build
   ```

## 4. Connecting a real MT5 account

The `MetaTrader5` Python package only installs and runs on Windows, against a
locally running MT5 terminal — it cannot run inside this project's Linux
Docker images. To go live:

1. On a Windows machine, install the MT5 terminal and log into your broker
   account through it (or leave it on the login screen — the Python SDK can
   authenticate itself).
2. Run the backend directly on that machine (not in Docker):
   ```bash
   pip install -r requirements.txt
   pip install MetaTrader5   # commented out in requirements.txt by default
   ```
3. In `.env`:
   ```
   BROKER_MODE=mt5
   MT5_LOGIN=12345678
   MT5_PASSWORD=your-password
   MT5_SERVER=YourBroker-Server
   MT5_TERMINAL_PATH=C:\Program Files\MetaTrader 5\terminal64.exe
   ```
4. Restart the backend. `services/broker/mt5_gateway.py` handles the real
   connection; every other module (analysis, strategies, risk, journal, API,
   frontend) is broker-agnostic and needs no changes.

## 5. Enabling AI narration & screenshot analysis

1. Get an API key from https://console.anthropic.com/.
2. In `backend/.env`:
   ```
   ANTHROPIC_API_KEY=sk-ant-...
   ```
3. Restart the backend. The `/analysis/narrative` endpoint, the "AI
   Narrative" button in the dashboard, and the screenshot analyzer will now
   work. Without a key, the rest of the app (analysis, setups, risk,
   journal) continues to work normally — AI narration degrades gracefully
   rather than blocking anything (see `docs/ARCHITECTURE.md`).

## 6. Enabling the Telegram bot

1. Create a bot via [@BotFather](https://t.me/BotFather) and copy its token.
2. In `backend/.env`:
   ```
   TELEGRAM_ENABLED=true
   TELEGRAM_BOT_TOKEN=123456:ABC-your-token
   ```
3. Restart the backend — it starts polling for updates automatically (see
   the `lifespan` handler in `app/main.py`).
4. Message your bot on Telegram and send `/start` to subscribe, or add a
   chat ID manually from the dashboard's Telegram page.

## Troubleshooting

- **"CREDENTIAL_ENCRYPTION_KEY is not set"** when adding a broker account —
  see step 1's "Generating a credential encryption key".
- **`/analysis/narrative` or screenshot analysis returns 502** —
  `ANTHROPIC_API_KEY` isn't set; this is expected until you complete step 5.
- **Telegram commands don't respond** — confirm `TELEGRAM_ENABLED=true` and
  check the backend logs for "Telegram bot polling started."; a missing/
  invalid token logs a warning instead of crashing the app.
- **SQLite "database is locked"** under concurrent load — expected under
  heavy concurrent writes; switch to Postgres (see above) for anything
  beyond single-user local use.
- **This sandboxed session could not run `docker build`/`docker compose up`**
  end-to-end (no Docker daemon available in this container-in-container
  environment) — the Dockerfiles and compose file were validated via
  `docker compose config` and careful manual review, but have not been
  build-tested here. Please verify `docker compose up --build` on your own
  machine before relying on it, and report back if anything doesn't build.
