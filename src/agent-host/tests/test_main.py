from fastapi.testclient import TestClient
from starlette.responses import JSONResponse

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


def test_messages_uses_m365_agents_sdk_process(monkeypatch) -> None:
    monkeypatch.setenv("ALLOW_MOCK_FOUNDRY", "true")
    _clear_settings_cache()
    called: dict[str, object] = {}

    async def fake_start_agent_process(request, agent_application, adapter):
        called["request"] = request
        called["agent_application"] = agent_application
        called["adapter"] = adapter
        return JSONResponse({"status": "processed"})

    monkeypatch.setattr("app.main.start_agent_process", fake_start_agent_process)
    client = TestClient(app)

    response = client.post("/api/messages", json={"type": "message", "text": "status?"})

    assert response.status_code == 200
    assert response.json() == {"status": "processed"}
    assert called["request"] is not None
    assert called["agent_application"] is not None
    assert called["adapter"] is not None
