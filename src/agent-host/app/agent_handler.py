from typing import Any
from uuid import uuid4

from app.foundry_client import FoundryAgent
from app.streaming import Citation, buffer_updates


class AgentHandler:
    def __init__(self, foundry: FoundryAgent) -> None:
        self._foundry = foundry

    async def handle_activity(
        self,
        activity: dict[str, Any],
        *,
        user_token: str | None = None,
    ) -> dict[str, Any]:
        text = (activity.get("text") or "").strip()
        conversation_id = _conversation_id(activity)
        if not text:
            return _message_response("Please send a message for the OperationsEngineering agent.")

        response_text, citations = await buffer_updates(
            self._foundry.stream_message(
                text,
                conversation_id=conversation_id,
                user_token=user_token,
            )
        )
        return _message_response(_append_citations(response_text, citations))


def _conversation_id(activity: dict[str, Any]) -> str:
    conversation = activity.get("conversation") or {}
    return conversation.get("id") or activity.get("conversationId") or str(uuid4())


def _message_response(text: str) -> dict[str, Any]:
    return {"type": "message", "text": text}


def _append_citations(text: str, citations: list[Citation]) -> str:
    if not citations:
        return text

    references = []
    for index, citation in enumerate(citations, start=1):
        label = citation.title
        if citation.url:
            label = f"[{label}]({citation.url})"
        details = citation.filepath or citation.chunk_id
        if details:
            label = f"{label} — {details}"
        references.append(f"{index}. {label}")

    return f"{text}\n\n**References**\n" + "\n".join(references)
