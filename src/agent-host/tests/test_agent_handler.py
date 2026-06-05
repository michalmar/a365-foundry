from app.agent_handler import AgentHandler
from app.foundry_client import MockFoundryAgentClient


async def test_handler_returns_foundry_response_with_citations() -> None:
    handler = AgentHandler(MockFoundryAgentClient())

    response = await handler.handle_activity({"text": "hello", "conversation": {"id": "c1"}})

    assert response["type"] == "message"
    assert "hello" in response["text"]
    assert response["attachments"][0]["content"]["title"] == "Local mock citation"
