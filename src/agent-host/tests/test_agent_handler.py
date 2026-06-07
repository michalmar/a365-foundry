from app.agent_handler import AgentHandler
from app.foundry_client import MockFoundryAgentClient


async def test_handler_returns_foundry_response_with_citations() -> None:
    handler = AgentHandler(MockFoundryAgentClient())

    response = await handler.handle_activity({"text": "hello", "conversation": {"id": "c1"}})

    assert response["type"] == "message"
    assert "hello" in response["text"]
    assert "**References**" in response["text"]
    assert "Local mock citation" in response["text"]
    assert "attachments" not in response
