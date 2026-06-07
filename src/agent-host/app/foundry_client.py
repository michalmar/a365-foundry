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
        self._agent_id: str | None = settings.foundry_agent_id

    async def stream_message(
        self, user_text: str, *, conversation_id: str | None = None, user_token: str | None = None
    ) -> AsyncIterable[AgentUpdate]:
        if not self._settings.project_endpoint:
            raise FoundryClientError("PROJECT_ENDPOINT is required for live Foundry calls")

        client = self._get_project_client()
        agent_id = self._agent_id or self._resolve_agent_id(client)
        self._agent_id = agent_id

        # The current Foundry SDK may expose sync or async methods depending on version.
        # Keep the surface isolated here and return buffered updates when streaming is unavailable.
        agents = getattr(client, "agents", None)
        if agents is None:
            raise FoundryClientError("azure-ai-projects client does not expose an agents client")

        thread = self._call_first_existing(agents, ["create_thread", "threads.create"])
        thread_id = getattr(thread, "id", None) or getattr(thread, "thread_id", None)
        if not thread_id:
            raise FoundryClientError("Unable to create Foundry thread")

        self._call_first_existing(
            agents,
            ["create_message", "messages.create"],
            thread_id=thread_id,
            role="user",
            content=user_text,
        )
        run = self._call_first_existing(
            agents,
            ["create_run", "runs.create_and_process", "runs.create"],
            thread_id=thread_id,
            agent_id=agent_id,
        )
        status = getattr(run, "status", "completed")
        if status not in {"completed", "succeeded", None}:
            raise FoundryClientError(f"Foundry run did not complete successfully: {status}")

        messages = self._call_first_existing(
            agents,
            ["list_messages", "messages.list"],
            thread_id=thread_id,
        )
        text, citations = self._extract_latest_assistant_message(messages)
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
        )
        return self._project_client

    def _resolve_agent_id(self, client: Any) -> str:
        agents = getattr(client, "agents", None)
        if agents is None:
            raise FoundryClientError("azure-ai-projects client does not expose an agents client")
        foundry_agent_name = self._settings.foundry_agent
        listed_agents = self._call_first_existing(agents, ["list_agents", "list"])
        for agent in listed_agents:
            if getattr(agent, "name", None) == foundry_agent_name:
                agent_id = getattr(agent, "id", None)
                if agent_id:
                    return agent_id
        raise FoundryClientError(f"Foundry agent not found by name: {foundry_agent_name}")

    def _call_first_existing(self, root: Any, names: list[str], **kwargs: Any) -> Any:
        for dotted_name in names:
            target = root
            for part in dotted_name.split("."):
                target = getattr(target, part, None)
                if target is None:
                    break
            if callable(target):
                try:
                    return target(**kwargs)
                except TypeError:
                    positional = [
                        kwargs[key]
                        for key in ("thread_id", "role", "content", "agent_id")
                        if key in kwargs
                    ]
                    return target(*positional)
        raise FoundryClientError("None of these Foundry SDK methods exist: " + ", ".join(names))

    def _extract_latest_assistant_message(self, messages: Any) -> tuple[str, list[Citation]]:
        iterable = getattr(messages, "data", messages)
        for message in iterable:
            if getattr(message, "role", None) != "assistant":
                continue
            return self._extract_text_and_citations(message)
        raise FoundryClientError("No assistant message returned from Foundry run")

    def _extract_text_and_citations(self, message: Any) -> tuple[str, list[Citation]]:
        content = getattr(message, "content", "")
        citations: list[Citation] = []
        if isinstance(content, str):
            return content, citations

        text_parts: list[str] = []
        for part in content or []:
            text = getattr(part, "text", None) or getattr(part, "value", None)
            if isinstance(text, str):
                text_parts.append(text)
            annotations = getattr(part, "annotations", []) or []
            for annotation in annotations:
                title = getattr(annotation, "title", None) or getattr(annotation, "file_name", None)
                if title:
                    citations.append(
                        Citation(
                            title=title,
                            url=getattr(annotation, "url", None),
                            filepath=getattr(annotation, "file_path", None),
                            chunk_id=getattr(annotation, "chunk_id", None),
                        )
                    )
        return "".join(text_parts), citations
