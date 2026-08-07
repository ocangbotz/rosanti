"""End-to-end API tests through FastAPI's TestClient — exercises the actual
router wiring, dependency injection, and request/response schema
validation (the layer the M1-M10 unit tests don't touch, since they call
the underlying modules directly).

The app's `lifespan` is deliberately NOT triggered here (no `with
TestClient(app) as client:`) — that would start the real background
scheduler and Telegram polling against the live singletons. Route wiring
was already verified against a real running uvicorn process during
development; here we only need the ASGI routing + dependency graph, which
works without lifespan.
"""

from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api import deps
from app.database import models  # noqa: F401 -- registers all models on Base.metadata
from app.database.base import Base
from app.main import app


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    test_session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

    def override_get_db() -> Generator:
        db = test_session_local()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    app.dependency_overrides[deps.get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_health_check(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_get_ohlc(client: TestClient):
    response = client.get(
        "/api/v1/market/ohlc", params={"symbol": "EURUSD", "timeframe": "H1", "count": 260}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["symbol"] == "EURUSD"
    assert len(body["candles"]) == 260


def test_get_positions_empty_by_default(client: TestClient):
    response = client.get("/api/v1/market/positions")
    assert response.status_code == 200
    assert response.json() == []


def test_get_market_analysis(client: TestClient):
    response = client.get(
        "/api/v1/analysis", params={"symbol": "EURUSD", "timeframe": "H1", "count": 260}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["symbol"] == "EURUSD"
    assert body["structure"]["trend"] in {"BUY", "SELL", "NEUTRAL"}


def test_narrative_without_ai_key_returns_502(client: TestClient):
    response = client.get("/api/v1/analysis/narrative", params={"symbol": "EURUSD"})
    assert response.status_code == 502
    assert "ANTHROPIC_API_KEY" in response.json()["detail"]


def test_generate_setup_without_ai_narrative_succeeds(client: TestClient):
    response = client.post(
        "/api/v1/setups/generate",
        json={"symbol": "EURUSD", "timeframe": "H1", "include_ai_narrative": False},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["symbol"] == "EURUSD"
    assert body["direction"] in {"BUY", "SELL"}
    assert isinstance(body["reasons"], list)


def test_generate_setup_requesting_ai_narrative_does_not_fail_without_key(client: TestClient):
    # AI narration is best-effort: no ANTHROPIC_API_KEY configured must
    # degrade gracefully rather than break setup generation. When a valid
    # setup was found, the missing narrative comes back as None; when the
    # generator instead rejected the trade, `ai_narrative` carries the
    # rejection reason as a fallback explanation — either way, never a 5xx.
    response = client.post(
        "/api/v1/setups/generate",
        json={"symbol": "EURUSD", "timeframe": "H1", "include_ai_narrative": True},
    )
    assert response.status_code == 200
    body = response.json()
    if body["status"] == "PROPOSED":
        assert body["ai_narrative"] is None
    else:
        assert isinstance(body["ai_narrative"], str) and body["ai_narrative"]


def test_list_setups_after_generating_one(client: TestClient):
    client.post(
        "/api/v1/setups/generate",
        json={"symbol": "GBPUSD", "timeframe": "H1", "include_ai_narrative": False},
    )
    response = client.get("/api/v1/setups", params={"page": 1, "page_size": 10})
    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 1
    assert body["items"][0]["symbol"] in {"GBPUSD"}


def test_get_and_patch_setup_status(client: TestClient):
    generated = client.post(
        "/api/v1/setups/generate",
        json={"symbol": "EURUSD", "timeframe": "H1", "include_ai_narrative": False},
    ).json()

    get_response = client.get(f"/api/v1/setups/{generated['id']}")
    assert get_response.status_code == 200

    patch_response = client.patch(
        f"/api/v1/setups/{generated['id']}/status", params={"new_status": "TAKEN"}
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["status"] == "TAKEN"


def test_get_setup_404(client: TestClient):
    response = client.get("/api/v1/setups/999999")
    assert response.status_code == 404


def test_lot_size_endpoint(client: TestClient):
    response = client.post(
        "/api/v1/risk/lot-size",
        json={
            "account_balance": 10_000,
            "risk_percent": 1.0,
            "entry_price": 1.1000,
            "stop_loss": 1.0950,
            "symbol": "EURUSD",
        },
    )
    assert response.status_code == 200
    assert response.json()["lot_size"] == pytest.approx(0.2)


def test_breakeven_endpoint(client: TestClient):
    response = client.post(
        "/api/v1/risk/breakeven",
        json={
            "entry_price": 1.1000,
            "stop_loss": 1.0950,
            "current_price": 1.1050,
            "direction": "BUY",
            "trigger_r": 1.0,
        },
    )
    assert response.status_code == 200
    assert response.json()["breakeven_reached"] is True


def test_journal_entry_crud_flow(client: TestClient):
    create_response = client.post(
        "/api/v1/journal/entries",
        json={
            "symbol": "EURUSD",
            "direction": "BUY",
            "entry_price": 1.1000,
            "stop_loss": 1.0950,
            "take_profit": 1.1150,
            "lot_size": 0.1,
            "opened_at": datetime.now(UTC).isoformat(),
        },
    )
    assert create_response.status_code == 200
    entry_id = create_response.json()["id"]

    get_response = client.get(f"/api/v1/journal/entries/{entry_id}")
    assert get_response.status_code == 200
    assert get_response.json()["outcome"] == "PENDING"

    patch_response = client.patch(
        f"/api/v1/journal/entries/{entry_id}",
        json={
            "exit_price": 1.1100,
            "closed_at": datetime.now(UTC).isoformat(),
            "profit_loss": 100.0,
        },
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["outcome"] == "WIN"

    list_response = client.get("/api/v1/journal/entries")
    assert list_response.status_code == 200
    assert list_response.json()["total"] >= 1

    delete_response = client.delete(f"/api/v1/journal/entries/{entry_id}")
    assert delete_response.status_code == 204
    assert client.get(f"/api/v1/journal/entries/{entry_id}").status_code == 404


def test_journal_reports(client: TestClient):
    for endpoint in ("win-rate", "weekly", "monthly"):
        response = client.get(f"/api/v1/journal/reports/{endpoint}")
        assert response.status_code == 200


def test_news_upcoming(client: TestClient):
    response = client.get("/api/v1/news/upcoming", params={"lookahead_minutes": 60})
    assert response.status_code == 200
    assert response.json()["has_high_impact_soon"] is False


def test_telegram_subscriber_lifecycle(client: TestClient):
    create_response = client.post(
        "/api/v1/telegram/subscribers", json={"chat_id": "999", "username": "trader"}
    )
    assert create_response.status_code == 200

    list_response = client.get("/api/v1/telegram/subscribers")
    assert any(s["chat_id"] == "999" for s in list_response.json())

    patch_response = client.patch(
        "/api/v1/telegram/subscribers/999", json={"notify_daily_summary": False}
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["notify_daily_summary"] is False

    delete_response = client.delete("/api/v1/telegram/subscribers/999")
    assert delete_response.status_code == 204


def test_telegram_test_message_without_token_fails_cleanly(client: TestClient):
    response = client.post("/api/v1/telegram/test-message", json={"message": "hello"})
    assert response.status_code == 502


def test_app_settings_upsert_and_get(client: TestClient):
    put_response = client.put(
        "/api/v1/settings/default_symbol",
        json={"key": "default_symbol", "value": {"symbol": "XAUUSD"}},
    )
    assert put_response.status_code == 200

    get_response = client.get("/api/v1/settings/default_symbol")
    assert get_response.status_code == 200
    assert get_response.json()["value"] == {"symbol": "XAUUSD"}


def test_app_setting_not_found(client: TestClient):
    response = client.get("/api/v1/settings/does-not-exist")
    assert response.status_code == 404


def test_screenshot_analyze_rejects_unsupported_content_type(client: TestClient):
    response = client.post(
        "/api/v1/screenshot/analyze",
        files={"file": ("chart.txt", b"not an image", "text/plain")},
    )
    assert response.status_code == 422
    assert "Unsupported image type" in response.json()["detail"]


def test_live_account_info(client: TestClient):
    response = client.get("/api/v1/accounts/live")
    assert response.status_code == 200
    body = response.json()
    assert body["currency"] == "USD"
    assert body["connected"] is True


def test_create_and_list_broker_account(client: TestClient):
    # Credential encryption requires a real Fernet key; mutate the cached
    # settings singleton in-place so the router's CredentialCipher() picks
    # it up without needing a .env file in the test environment.
    from cryptography.fernet import Fernet

    from app.config import get_settings

    get_settings().credential_encryption_key = Fernet.generate_key().decode()

    create_response = client.post(
        "/api/v1/accounts",
        json={"login": 555111, "password": "hunter2", "server": "Demo-Server"},
    )
    assert create_response.status_code == 200
    assert "password" not in create_response.json()

    list_response = client.get("/api/v1/accounts")
    assert list_response.status_code == 200
    assert any(a["login"] == 555111 for a in list_response.json())
