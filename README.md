# A365 Foundry

Scaffold for surfacing the existing Azure AI Foundry `OperationsEngineering` agent as a Microsoft 365 custom engine agent.

Implemented tenant-free pieces from the PRD:

- Python FastAPI agent host under `/src/agent-host`
- Foundry adapter boundary with offline mock mode and live Azure AI Projects wiring
- OBO/auth adapter boundaries that fail closed for production-only tenant work
- Microsoft 365 app package manifest with `copilotAgents.customEngineAgents`
- Azure Container Apps, managed identity, Azure Bot Service, and App Insights Bicep modules
- GitHub Actions validation/deployment workflow

## Validate locally

```bash
cd src/agent-host
export ALLOW_MOCK_FOUNDRY=true
uv sync
uv run ruff check .
uv run pytest
```

## What still requires Azure/M365 tenant access

- Registering/consenting Entra applications and delegated scopes
- Enabling and validating the Bot Service Teams/Copilot channels
- Sideloading/publishing the app package in Teams/M365 admin center
- Verifying live Foundry agent invocation, OBO traces, streaming, and production citations
