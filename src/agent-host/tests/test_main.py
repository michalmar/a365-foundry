from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app


def _clear_settings_cache() -> None:
    get_settings.cache_clear()


def test_healthz_uses_mock_foundry(monkeypatch) -> None:
    monkeypatch.setenv("ALLOW_MOCK_FOUNDRY", "true")
    _clear_settings_cache()
    client = TestClient(app)

    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json()["mockFoundry"] is True


def test_messages_returns_mock_response(monkeypatch) -> None:
    monkeypatch.setenv("ALLOW_MOCK_FOUNDRY", "true")
    _clear_settings_cache()
    client = TestClient(app)

    response = client.post("/api/messages", json={"type": "message", "text": "status?"})

    assert response.status_code == 200
    assert "status?" in response.json()["text"]
