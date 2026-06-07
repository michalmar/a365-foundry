# A365 Foundry

Scaffold for surfacing the existing Azure AI Foundry `OperationsEngineering` agent as a Microsoft 365 custom engine agent.

Implemented tenant-free pieces from the PRD:

- Python FastAPI agent host under `/src/agent-host`
- Foundry adapter boundary with offline mock mode and live Azure AI Projects wiring
- Microsoft 365 Agents SDK `/api/messages` adapter with local and managed-identity connection modes
- OBO boundary for future Graph/LOB delegated-token calls
- Microsoft 365 app package manifest with `copilotAgents.customEngineAgents`
- Azure Container Apps, managed identity, Azure Bot Service, and App Insights Bicep modules
- GitHub Actions validation/deployment workflow

## Deployed Azure shape

The production deployment uses a user-assigned managed identity for both Azure Bot Service and the Container App. The M365 app package reuses that deployed Bot identity; it does not create a separate bot app registration.

To prepare a package environment, copy `src/env/.env.example` to `src/env/.env.<name>` and set:

- `BOT_ID` — the deployment output `botId`
- `BOT_DOMAIN` — the deployment output `containerAppFqdn`
- `TEAMS_APP_ID` — leave blank for the first toolkit run so `teamsApp/create` can populate it

## Validate locally

```bash
cd src/agent-host
export ALLOW_MOCK_FOUNDRY=true
uv sync
uv run ruff check .
uv run pytest
```

## What still requires M365 tenant access

- Enabling and validating the Bot Service Teams/Copilot channels
- Sideloading/publishing the app package in Teams/M365 admin center
- Verifying a live Teams/Copilot conversation and any future OBO Graph/LOB delegated-token flows
