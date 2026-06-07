import sys
from types import ModuleType

from app.config import Settings
from app.foundry_client import FoundryAgentClient
from app.streaming import buffer_updates


def test_get_project_client_uses_default_credential_and_preview(monkeypatch) -> None:
    created: dict[str, object] = {}

    class FakeDefaultAzureCredential:
        pass

    class FakeAIProjectClient:
        def __init__(self, *, endpoint: str, credential: object, allow_preview: bool) -> None:
            created["endpoint"] = endpoint
            created["credential"] = credential
            created["allow_preview"] = allow_preview

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
    assert created["allow_preview"] is True


async def test_stream_message_uses_agent_reference_response_api() -> None:
    created: dict[str, object] = {}

    class Response:
        output_text = "done"
        output = []

    class Responses:
        def create(self, **kwargs: object) -> Response:
            created.update(kwargs)
            return Response()

    class OpenAIClient:
        responses = Responses()

    class FakeProjectClient:
        def get_openai_client(self) -> OpenAIClient:
            return OpenAIClient()

    settings = Settings(
        PROJECT_ENDPOINT="https://foundry.example.test/api/projects/demo",
        FOUNDRY_AGENT="OperationsEngineering",
        FOUNDRY_AGENT_VERSION="9",
    )
    client = FoundryAgentClient(settings, project_client_factory=FakeProjectClient)

    text, citations = await buffer_updates(client.stream_message("hello"))

    assert text == "done"
    assert citations == []
    assert created == {
        "input": [{"role": "user", "content": "hello"}],
        "extra_body": {
            "agent_reference": {
                "name": "OperationsEngineering",
                "version": "9",
                "type": "agent_reference",
            }
        },
    }
