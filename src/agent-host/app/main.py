from typing import Annotated, Any

from fastapi import Depends, FastAPI, Request
from microsoft_agents.hosting.fastapi import start_agent_process

from app.agent_handler import AgentHandler
from app.config import Settings, get_settings
from app.foundry_client import FoundryAgentClient, MockFoundryAgentClient
from app.m365_adapter import create_agent_application, create_cloud_adapter

app = FastAPI(title="A365 Foundry Custom Engine Agent", version="0.1.0")


def get_foundry(
    settings: Annotated[Settings, Depends(get_settings)],
) -> FoundryAgentClient | MockFoundryAgentClient:
    if settings.should_use_mock_foundry:
        return MockFoundryAgentClient()
    return FoundryAgentClient(settings)


def get_handler(
    foundry: Annotated[
        FoundryAgentClient | MockFoundryAgentClient,
        Depends(get_foundry),
    ],
) -> AgentHandler:
    return AgentHandler(foundry)


@app.get("/healthz")
async def healthz(settings: Annotated[Settings, Depends(get_settings)]) -> dict[str, Any]:
    return {
        "status": "ok",
        "foundryAgent": settings.foundry_agent,
        "mockFoundry": settings.should_use_mock_foundry,
    }


@app.post("/api/messages", response_model=None)
async def messages(
    request: Request,
    handler: Annotated[AgentHandler, Depends(get_handler)],
) -> Any:
    return await start_agent_process(
        request,
        create_agent_application(handler),
        create_cloud_adapter(get_settings()),
    )
