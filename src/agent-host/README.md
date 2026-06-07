# A365 Foundry Agent Host

Python FastAPI scaffold for a Microsoft 365 custom engine agent that proxies the existing Azure AI Foundry agent named `OperationsEngineering`.

This scaffold is intentionally runnable without Azure or Microsoft 365 tenant access for local validation. Production Azure/M365 calls are isolated behind adapters and configuration gates.

## Local validation

```bash
export ALLOW_MOCK_FOUNDRY=true
uv sync
uv run ruff check .
uv run pytest
uv run uvicorn app.main:app --reload --port 3978
```

## Required production configuration

Copy `.env.example` to `.env` for local development, then provide equivalent Container Apps secrets/environment variables in Azure:

- `PROJECT_ENDPOINT` — Azure AI Foundry project endpoint
- `FOUNDRY_AGENT` — Foundry agent name, defaults to `OperationsEngineering`
- `FOUNDRY_AGENT_VERSION` — optional next-gen Foundry agent version used in `agent_reference`
- `AZURE_TENANT` and `M365_TENANT`
- `BOT_ID` — user-assigned managed identity client id used by Azure Bot Service
- `REQUIRE_BOT_AUTH=true` to use the Microsoft 365 Agents SDK adapter with the configured Bot identity

The production container uses Python 3.13. The local project allows Python 3.12+ so CI and developer machines can run the offline tests before tenant provisioning.

The Container App identity also needs the `Foundry User` role on the Azure AI Foundry account that hosts the project. The Bicep deployment assigns this when `foundryAccountResourceGroup` and `foundryAccountName` are provided.
