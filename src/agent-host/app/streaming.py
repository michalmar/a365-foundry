from collections.abc import AsyncIterable
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Citation:
    title: str
    url: str | None = None
    filepath: str | None = None
    chunk_id: str | None = None

    def to_attachment(self) -> dict[str, str]:
        payload = {"title": self.title}
        if self.url:
            payload["url"] = self.url
        if self.filepath:
            payload["filepath"] = self.filepath
        if self.chunk_id:
            payload["chunkId"] = self.chunk_id
        return payload


@dataclass(frozen=True)
class AgentUpdate:
    text_delta: str = ""
    citations: list[Citation] = field(default_factory=list)
    done: bool = False


async def buffer_updates(updates: AsyncIterable[AgentUpdate]) -> tuple[str, list[Citation]]:
    text_parts: list[str] = []
    citations: list[Citation] = []
    seen: set[tuple[str, str | None, str | None, str | None]] = set()
    async for update in updates:
        if update.text_delta:
            text_parts.append(update.text_delta)
        for citation in update.citations:
            key = (citation.title, citation.url, citation.filepath, citation.chunk_id)
            if key not in seen:
                citations.append(citation)
                seen.add(key)
    return "".join(text_parts), citations
