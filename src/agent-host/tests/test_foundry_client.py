import sys
from types import ModuleType

from app.config import Settings
from app.foundry_client import FoundryAgentClient


def test_get_project_client_uses_default_credential(monkeypatch) -> None:
    created: dict[str, object] = {}

    class FakeDefaultAzureCredential:
        pass

    class FakeAIProjectClient:
        def __init__(self, *, endpoint: str, credential: object) -> None:
            created["endpoint"] = endpoint
            created["credential"] = credential

    azure_module = ModuleType("azure")
    ai_module = ModuleType("azure.ai")
    projects_module = ModuleType("azure.ai.projects")
    identity_module = ModuleType("azure.identity")
    projects_module.AIProjectClient = FakeAIProjectClient
    identity_module.DefaultAzureCredential = FakeDefaultAzureCredential

    monkeypatch.setitem(sys.modules, "azure", azure_module)
    monkeypatch.setitem(sys.modules, "azure.ai", ai_module)
    monkeypatch.setitem(sys.modules, "azure.ai.projects", projects_module)
    monkeypatch.setitem(sys.modules, "azure.identity", identity_module)

    settings = Settings(
        PROJECT_ENDPOINT="https://foundry.example.test/api/projects/demo",
        FOUNDRY_AGENT="OperationsEngineering",
    )

    project_client = FoundryAgentClient(settings)._get_project_client()

    assert isinstance(project_client, FakeAIProjectClient)
    assert created["endpoint"] == "https://foundry.example.test/api/projects/demo"
    assert isinstance(created["credential"], FakeDefaultAzureCredential)
