from collections.abc import AsyncIterable, Callable
from typing import Any, Protocol

from app.config import Settings
from app.streaming import AgentUpdate, Citation


class FoundryClientError(RuntimeError):
    pass


class FoundryAgent(Protocol):
    async def stream_message(
        self, user_text: str, *, conversation_id: str | None = None, user_token: str | None = None
    ) -> AsyncIterable[AgentUpdate]: ...


class MockFoundryAgentClient:
    """Offline Foundry stand-in for tests and tenant-free local development."""

    async def stream_message(
        self, user_text: str, *, conversation_id: str | None = None, user_token: str | None = None
    ) -> AsyncIterable[AgentUpdate]:
        yield AgentUpdate(text_delta=f"OperationsEngineering mock response: {user_text}")
        citation = Citation(
            title="Local mock citation",
            filepath="docs/PRD-Foundry-Agent-in-M365-Copilot.md",
        )
        yield AgentUpdate(citations=[citation], done=True)


class FoundryAgentClient:
    """Azure AI Foundry Agents adapter.

    Live Azure calls are kept behind this adapter so handlers and tests can run without
    tenant access.
    """

    def __init__(
        self,
        settings: Settings,
        *,
        project_client_factory: Callable[[], Any] | None = None,
    ) -> None:
        self._settings = settings
        self._project_client_factory = project_client_factory
        self._project_client: Any | None = None

    async def stream_message(
        self, user_text: str, *, conversation_id: str | None = None, user_token: str | None = None
    ) -> AsyncIterable[AgentUpdate]:
        if not self._settings.project_endpoint:
            raise FoundryClientError("PROJECT_ENDPOINT is required for live Foundry calls")

        project_client = self._get_project_client()
        openai_client = project_client.get_openai_client()
        response = openai_client.responses.create(
            input=[{"role": "user", "content": user_text}],
            extra_body={"agent_reference": self._agent_reference()},
        )
        text = getattr(response, "output_text", None)
        if not isinstance(text, str):
            raise FoundryClientError("Foundry response did not include output_text")
        citations = self._extract_response_citations(response)
        yield AgentUpdate(text_delta=text, citations=citations, done=True)

    def _get_project_client(self) -> Any:
        if self._project_client is not None:
            return self._project_client
        if self._project_client_factory is not None:
            self._project_client = self._project_client_factory()
            return self._project_client

        try:
            from azure.ai.projects import AIProjectClient
            from azure.identity import DefaultAzureCredential
        except ImportError as exc:
            raise FoundryClientError("azure-ai-projects and azure-identity are required") from exc

        self._project_client = AIProjectClient(
            endpoint=self._settings.project_endpoint,
            credential=DefaultAzureCredential(),
            allow_preview=True,
        )
        return self._project_client

    def _agent_reference(self) -> dict[str, str]:
        reference = {
            "name": self._settings.foundry_agent,
            "type": "agent_reference",
        }
        if self._settings.foundry_agent_version:
            reference["version"] = self._settings.foundry_agent_version
        return reference

    def _extract_response_citations(self, response: Any) -> list[Citation]:
        citations: list[Citation] = []
        for annotation in _walk_annotations(getattr(response, "output", []) or []):
            title = (
                _get_value(annotation, "title")
                or _get_value(annotation, "file_name")
                or _get_value(annotation, "filename")
            )
            if title:
                citations.append(
                    Citation(
                        title=title,
                        url=_get_value(annotation, "url"),
                        filepath=_get_value(annotation, "file_path")
                        or _get_value(annotation, "filepath"),
                        chunk_id=_get_value(annotation, "chunk_id")
                        or _get_value(annotation, "chunkId"),
                    )
                )
        return citations


def _walk_annotations(value: Any) -> list[Any]:
    annotations: list[Any] = []
    if isinstance(value, dict):
        nested_annotations = value.get("annotations")
        if isinstance(nested_annotations, list):
            annotations.extend(nested_annotations)
        for nested in value.values():
            annotations.extend(_walk_annotations(nested))
    elif isinstance(value, list):
        for item in value:
            annotations.extend(_walk_annotations(item))
    else:
        nested_annotations = getattr(value, "annotations", None)
        if isinstance(nested_annotations, list):
            annotations.extend(nested_annotations)
        for attr in ("content", "output", "text"):
            nested = getattr(value, attr, None)
            if nested is not None:
                annotations.extend(_walk_annotations(nested))
    return annotations


def _get_value(value: Any, key: str) -> str | None:
    if isinstance(value, dict):
        result = value.get(key)
    else:
        result = getattr(value, key, None)
    return result if isinstance(result, str) and result else None
