# AGENTS.md

## Global instructions
 - at each session set ENV variables for terminal to:
   - AZURE_CONFIG_DIR="$HOME/.azure-365"
   - COPILOT_HOME="$HOME/.copilot"
 - Python - always use UV to maintain Python

## Reusable implementation notes for Foundry-to-M365 custom engine agents

### Azure AI Foundry SDK
 - For next-generation Foundry agents, use `azure-ai-projects>=2.1.0` and the OpenAI-compatible responses client.
 - Use `AIProjectClient(endpoint=..., credential=DefaultAzureCredential(), allow_preview=True)`.
 - Invoke existing next-generation Foundry agents with `project_client.get_openai_client().responses.create(...)` and `extra_body={"agent_reference": {"name": "<agent-name>", "version": "<version>", "type": "agent_reference"}}`.
 - Prefer agent `name` plus optional `version` over legacy `asst...` identifiers.
 - Do not use the legacy `azure-ai-agents` thread/run API for next-generation Foundry agents unless the target resource is confirmed to be legacy.
 - Keep live Foundry access behind an adapter boundary so tests can use an offline mock without Azure or M365 tenant access.

### Python host and dependency management
 - Use UV for Python dependency resolution, locking, local execution, and container builds.
 - For FastAPI-based Microsoft 365 agents, include the Microsoft Agents SDK packages and import from the `microsoft_agents` namespace, not `microsoft.agents`.
 - `microsoft-agents-hosting-fastapi` may require an explicit `aiohttp` dependency even when the SDK imports it at runtime.
 - In Dockerfiles, copy `pyproject.toml`, `uv.lock`, `README.md`, and the application package before running `uv sync --frozen --no-dev` when the Python package metadata references those files.

### Microsoft 365 Agents SDK and Bot Framework
 - Use the SDK FastAPI entrypoint, for example `start_agent_process(request, agent_application, adapter)`, instead of hand-rolling `/api/messages` request handling.
 - For Azure Bot Service with a user-assigned managed identity, configure:
   - `msaAppType='UserAssignedMSI'`
   - `msaAppId=<managed-identity-client-id>`
   - `msaAppTenantId=<tenant-guid>`
   - `msaAppMSIResourceId=<managed-identity-resource-id>`
 - Use a tenant GUID for Bot Service tenant fields. Domain-style tenant names can be valid elsewhere but are rejected for Bot resource identity configuration.
 - For production Container Apps, set `AZURE_CLIENT_ID` to the user-assigned managed identity client ID so `DefaultAzureCredential` selects the intended identity.
 - Assign the Container App managed identity `Foundry User` on the Foundry account scope for host-to-Foundry calls.

### Teams and Copilot manifest decisions
 - A custom engine agent package should bind the deployed bot through:
   - `bots[].botId=${{BOT_ID}}`
   - `copilotAgents.customEngineAgents[].id=${{BOT_ID}}`
   - `copilotAgents.customEngineAgents[].type="bot"`
 - `validDomains` should contain the host domain only, without `https://`.
 - `webApplicationInfo.id` should match the bot ID when the bot identity is the app identity.
 - `webApplicationInfo.resource` commonly follows `api://botid-${{BOT_ID}}` for Bot Framework based agents.
 - Reuse the deployed Azure Bot identity in the app package. Do not create a second bot AAD app in the toolkit flow unless the architecture intentionally uses a separate app registration.
 - Keep app package environment files local or ignored when they contain tenant-specific IDs. Commit only examples or templates.
 - Teams app packages must zip only `manifest.json`, `color.png`, and `outline.png` at the zip root.
 - Use a 192x192 color icon and a 32x32 outline icon; Teams rejects invalid icon dimensions.

### Response formatting for Teams/Bot Connector
 - Treat Bot Connector `400 Bad Request` on send-back as a possible invalid activity payload, not only as auth failure.
 - Be conservative with custom citation attachments/entities. Some Teams/Copilot surfaces reject unsupported attachment or entity shapes.
 - Prefer rendering citations as plain markdown references in the message text unless the target channel's supported citation schema is verified end-to-end.
 - Long Foundry responses with citations can exercise different Bot Connector validation paths than simple "hello" responses; test both.

### Azure Container Apps and infrastructure
 - For private ACR images, configure Container Apps registry pull with the user-assigned identity and assign `AcrPull` to that identity on the registry.
 - Make role assignment names deterministic with `guid(<scope-id>, <stable-principal-name>, <role-purpose>)`.
 - For role assignments to resources in another resource group, deploy the assignment from a Bicep module scoped to that resource group.
 - Keep deployment outputs for `botId`, `containerAppFqdn`, managed identity client ID, managed identity principal ID, and managed identity resource ID; these values drive app package generation and troubleshooting.