from typing import Any

from fastapi import Depends, FastAPI, Request

from app.agent_handler import AgentHandler
from app.auth.bot_auth import BotAuthValidator
from app.config import Settings, get_settings
from app.foundry_client import FoundryAgentClient, MockFoundryAgentClient

app = FastAPI(title="A365 Foundry Custom Engine Agent", version="0.1.0")


def get_foundry(settings: Settings = Depends(get_settings)) -> FoundryAgentClient | MockFoundryAgentClient:
    if settings.should_use_mock_foundry:
        return MockFoundryAgentClient()
    return FoundryAgentClient(settings)


def get_handler(foundry=Depends(get_foundry)) -> AgentHandler:
    return AgentHandler(foundry)


@app.get("/healthz")
async def healthz(settings: Settings = Depends(get_settings)) -> dict[str, Any]:
    return {
        "status": "ok",
        "foundryAgent": settings.foundry_agent,
        "mockFoundry": settings.should_use_mock_foundry,
    }


@app.post("/api/messages")
async def messages(
    request: Request,
    settings: Settings = Depends(get_settings),
    handler: AgentHandler = Depends(get_handler),
) -> dict[str, Any]:
    auth = await BotAuthValidator(settings).validate(request)
    activity = await request.json()
    return await handler.handle_activity(activity, user_token=auth.user_token)
