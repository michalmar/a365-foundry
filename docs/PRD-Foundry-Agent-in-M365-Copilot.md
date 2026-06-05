# PRD — Consuming an Azure AI Foundry Agent (Microsoft Agent Framework) in Microsoft 365 Copilot

| | |
|---|---|
| **Author** | Michal Marusan (Sr Solution Engineer, CZ-BPA) |
| **Status** | Draft for implementation |
| **Last updated** | 2026-06-05 |
| **Target implementers** | GitHub Copilot + engineering, with M365 / Azure admin support |
| **Source of truth** | Microsoft Learn (Foundry, M365 Agents SDK, Copilot extensibility), microsoft/Agents & Azure-Samples repos — see §15 |

> ⚠️ Several capabilities referenced here are **Preview / Early Access Preview** as of mid-2026 (direct Foundry→M365 publish, Copilot Studio Foundry connect, A2A tool). Re-verify GA status at build time. Microsoft Agent Framework (MAF) itself reached **GA v1.0 (~March 2026)**.

---

## 1. Summary

We have an AI agent already running in **Azure AI Foundry Agent Service**, authored with the **Microsoft Agent Framework (MAF)**. This PRD defines how to make that agent consumable by end users **inside Microsoft 365 Copilot** (and Teams), the recommended architecture, the components and scripts to build, the authentication model, and the M365 deployment/governance steps.

Because the agent **owns its own model and orchestration** (it is not just a set of tools for Copilot's built-in LLM), the correct M365 surface is a **Custom Engine Agent (CEA)** — not a declarative agent.

**Recommended delivery:** a two-track plan.
- **Track 1 (Pilot, days):** Direct **Publish to Teams + M365 Copilot** from the Foundry portal — fastest path to real user feedback. Accept preview limits (no streaming, no citations, no file/image in Copilot).
- **Track 2 (Production, weeks):** A **Custom Engine Agent built on the Microsoft 365 Agents SDK** in a proxy/host pattern — full control of streaming, citations, identity (OBO/SSO), and multi-channel delivery. This is the durable answer.

---

## 2. Problem statement & goals

### 2.1 Problem
End users live in M365 Copilot/Teams. Our Foundry/MAF agent's value is locked inside the Foundry playground. We need it surfaced where users already work, with enterprise identity, governance, and a production-grade UX.

### 2.2 Goals
- G1 — Users invoke the Foundry/MAF agent from M365 Copilot and Teams using their corporate identity.
- G2 — Responses preserve the agent's reasoning, tool use, streaming, and (production) citations.
- G3 — Downstream calls (Graph, line-of-business APIs) run **on behalf of the signed-in user** (OBO), not a service principal.
- G4 — Repeatable IaC + CI/CD; implementable by GitHub Copilot from this PRD.
- G5 — Admin-governed rollout (M365 admin approval, scoped publishing, observability).

### 2.3 Non-goals
- Re-authoring the agent's reasoning logic (the MAF agent stays the brain).
- Building a declarative agent that relies on Copilot's built-in orchestrator.
- Voice/telephony channels (future).

### 2.4 Success metrics
- Time-to-first-response < 3s; streamed tokens visible in production CEA.
- ≥ 95% of downstream calls use a user (OBO) token.
- Pilot in users' hands within 1 week; production CEA GA-track within 4–6 weeks.

---

## 3. Personas & user stories

- **End user (knowledge worker):** "From Copilot chat I ask the agent a domain question and get a grounded answer with citations, using my own permissions."
- **Maker/engineer:** "I deploy the agent to M365 from a repo with one pipeline run."
- **M365 / security admin:** "I approve, scope, monitor, and can revoke the agent; it has a governable identity."

---

## 4. Background (so Copilot has context)

- **Microsoft Agent Framework (MAF):** consolidated successor to Semantic Kernel + AutoGen. Native support for **A2A**, **MCP**, AG-UI. GA v1.0 ~March 2026. Surfaces models as `IChatClient` (.NET) / equivalent; agents as `ChatClientAgent` / `AIAgent` with `AIFunction` tools.
- **Azure AI Foundry Agent Service:** hosts the agent (model + tools + orchestration). New-portal agents expose a **project endpoint** + **Agent Id**. Foundry's **A2A tool** makes a Foundry agent an A2A *client*; the classic "Connected Agents" tool is removed in the new service (use A2A tool or Workflows).
- **M365 Copilot extensibility:**
  - **Declarative agent** = custom instructions/knowledge/tools on Copilot's own LLM/orchestrator.
  - **Custom Engine Agent (CEA)** = *you* bring the model + orchestration (Foundry/MAF), surfaced via **Azure Bot Service** + an app manifest. **This is our case.**
- **M365 Agents SDK:** model/orchestrator-agnostic bridge — "supports integration with Azure Foundry, Semantic Kernel, OpenAI Agents, LangChain, or custom-built solutions." Exposes `/api/messages`, registers with Azure Bot Service, publishes to Copilot/Teams.
- **M365 Agents Toolkit (VS Code):** scaffolds the app package — `manifest.json`, `m365agents.yml`, provisioning.

---

## 5. Options analysis & decision

| # | Path | Effort | Where logic runs | Status (mid-2026) | Key limitation | Use for |
|---|------|--------|------------------|-------------------|----------------|---------|
| A | **Direct Foundry → M365 publish** | Lowest | Foundry | Early Access Preview | No streaming/citations; no file/image in Copilot; no Private Link | **Pilot** |
| B | **Copilot Studio "Connect to Foundry agent"** | Low | Foundry + CS | Preview | New Foundry portal only; CS message metering | Multi-agent orchestration w/ CS |
| C | **CEA on M365 Agents SDK (proxy/host)** | High | Your host + Foundry | GA-track | You own infra/auth | **Production** |
| D | **A2A protocol** | Med-High | External host | Preview | Foundry-published agent ≠ A2A *server*; must host externally | Cross-vendor multi-agent |
| E | **MCP / declarative tool exposure** | Med | Copilot orchestrator | GA-ish | Not your model/orchestration | When Copilot's LLM is enough (not our case) |

**Decision:** **A for pilot, C for production.** Rationale: the requirement that the MAF/Foundry agent own its reasoning rules out declarative agents (E). Among CEA routes, the Agents SDK proxy/host (C) is the only one that is simultaneously GA-track, full-fidelity (streaming + citations), and identity-flexible (OBO/SSO). B and D are reserved for multi-agent scenarios.

---

## 6. Target architecture (Track 2 — production CEA)

```
[End user] ── chat ──> [M365 Copilot / Teams host]
                              │  manifest: copilotAgents.customEngineAgents
                              ▼
                    [Azure Bot Service]  ◄── Entra app reg (Bot identity)
                              │  POST /api/messages  (JWT validated)
                              ▼
        [M365 Agents SDK app — Azure Container Apps / App Service]
           • ActivityHandler / ChatClientAgent (MAF)
           • Streaming + citations adapter
           • OBO token exchange (user → downstream)
                              │  IChatClient / azure-ai-projects
                              ▼
                 [Azure AI Foundry Agent Service]
                   • model (gpt-4.1 / 4o) + tools + MCP
                              │  OBO user token
                              ▼
              [Microsoft Graph / LOB APIs / data sources]

Governance/build plane:
  [M365 Agents Toolkit (VS Code)] → app package (manifest.json, m365agents.yml)
  [Entra ID] → app registrations (bot + API), OBO, SSO
  [Teams / M365 Admin Center] → admin approval, scoped publish
  [App Insights / OpenTelemetry] → tracing & observability
```

**Manifest binding (Teams manifest v1.22):**
```json
"copilotAgents": { "customEngineAgents": [ { "id": "${{BOT_ID}}", "type": "bot" } ] }
```

---

## 7. Components to build

| ID | Component | Tech | Notes |
|----|-----------|------|-------|
| C1 | **Agents SDK host app** | .NET 8 ASP.NET Core (primary) or Python FastAPI | Exposes `/api/messages`; hosts/forwards to MAF agent |
| C2 | **Foundry connector** | `Microsoft.Extensions.AI` `IChatClient` / `azure-ai-projects` | Calls Foundry agent via project endpoint + Agent Id, or hosts MAF in-process |
| C3 | **Auth module** | Entra ID, OBO, Bot JWT validation | User SSO + downstream OBO; Managed Identity host→Foundry |
| C4 | **App package** | Teams manifest v1.22 + `m365agents.yml` | `copilotAgents.customEngineAgents` binding |
| C5 | **IaC** | Bicep/azd | Bot Service, Container App, Entra apps, App Insights, Managed Identity |
| C6 | **CI/CD** | GitHub Actions | Build, provision, deploy, package, publish |
| C7 | **Observability** | OpenTelemetry → App Insights | Trace turn → Foundry call → tool calls |

### Suggested repo layout
```
/src
  /agent-host            # C1/C2/C3 (.NET ASP.NET Core Agents SDK app)
    Program.cs
    AgentHandler.cs      # ActivityHandler → MAF agent / Foundry proxy
    Auth/OboTokenService.cs
  /appPackage            # C4
    manifest.json
    color.png  outline.png
  m365agents.yml
/infra                   # C5 (Bicep)
  main.bicep
  bot.bicep  containerapp.bicep  identity.bicep
/.github/workflows       # C6
  deploy.yml
azure.yaml               # azd config
README.md
```

---

## 8. Authentication & identity design

- **Inbound (Copilot/Teams → host):** Azure Bot Service posts to `/api/messages`; the Agents SDK validates the inbound JWT. Bot resource auth = **User-Assigned Managed Identity** (preferred) or Federated Credentials; avoid client secrets in production.
- **User SSO:** Teams/Copilot SSO surfaces the user token to the host.
- **Downstream (OBO):** exchange the user token for Graph/LOB scopes via **On-Behalf-Of**. Use the `obo-authorization` / `auto-signin` samples in microsoft/Agents as the reference.
- **Host → Foundry:** **Managed Identity** + `DefaultAzureCredential` (no API keys in prod). API keys are dev-only.
- **`agent.identity` must not be null** for the direct-publish path; publisher needs **Azure Bot Service Contributor** on the RG.
- **Governance (optional):** assign the agent an Entra **agent identity / Blueprint Identity** for observability and revocation.

**Entra app registrations:**
1. **Bot app** (multi/single-tenant) — used by Azure Bot Service; expose `api://botid-{appId}` for SSO.
2. **API/downstream scopes** — delegated permissions (Graph + LOB) consented for OBO.

---

## 9. Implementation plan (phased, GitHub-Copilot-ready)

### Phase 0 — Pilot via direct publish (Track 1)
1. `az provider register --namespace Microsoft.BotService`
2. Ensure publisher has **Azure Bot Service Contributor** on the target RG; ensure `agent.identity` is set.
3. Foundry portal → open tested agent version → **Publish → Publish to Teams and Microsoft 365 Copilot**.
4. Scope: **"Just you"** (no approval) for first validation; capture metadata (Name, version `major.minor.patch`, descriptions, Developer ≤32 chars).
5. Validate in Copilot; gather feedback. (Note preview gaps: no streaming/citations, no file/image in Copilot.)

### Phase 1 — Production CEA scaffold (Track 2)
1. Install **M365 Agents Toolkit** (VS Code) + **Agents SDK**.
2. Scaffold the CEA host (C1) with `/api/messages`.
3. Wire **C2 Foundry connector** (in-process MAF or proxy to Foundry project endpoint + Agent Id).
4. Add **manifest** binding (C4).

### Phase 2 — Identity & fidelity
5. Implement **OBO/SSO** (C3); Managed Identity host→Foundry.
6. Implement **streaming** + **citations** adapter (the production differentiators vs direct publish).

### Phase 3 — Infra, CI/CD, observability
7. **C5 Bicep**: Bot Service, Container App, Entra apps, Managed Identity, App Insights.
8. **C6 GitHub Actions**: build → provision (azd) → deploy → package → publish.
9. **C7 OpenTelemetry** tracing.

### Phase 4 — Publish & govern
10. Sideload app package for test; then **org-wide publish** with **M365 admin approval**.
11. Scope to a pilot group; monitor; iterate.

---

## 10. Reference code & scripts

> Patterns adapted from MIT/Apache-licensed Microsoft samples: `microsoft/Agents` (`samples/dotnet/Agent Framework/AgentFrameworkWeather`) and `Azure-Samples/m365-custom-engine-agents`. Treat as scaffolding — adjust namespaces/versions at build time.

### 10.1 .NET CEA host — MAF agent over `/api/messages`
```csharp
// Program.cs — ASP.NET Core M365 Agents SDK host wrapping a MAF agent
using Microsoft.Agents.AI;
using Microsoft.Extensions.AI;
using Azure.AI.OpenAI;
using Azure.Identity;

var builder = WebApplication.CreateBuilder(args);

// Foundry / Azure OpenAI surfaced as IChatClient (Managed Identity, no keys)
IChatClient chat = new AzureOpenAIClient(
        new Uri(builder.Configuration["Foundry:Endpoint"]!),
        new DefaultAzureCredential())
    .GetChatClient(builder.Configuration["Foundry:Deployment"] ?? "gpt-4.1")
    .AsIChatClient();

AIAgent agent = chat.CreateAIAgent(
    instructions: "You are <domain> assistant.",
    name: "FoundryCEA",
    tools: [ AIFunctionFactory.Create(MyTools.Lookup) ]);

builder.Services.AddSingleton(agent);
// builder.Services.AddAgentsSdk(...);  // register Agents SDK adapter + auth
var app = builder.Build();

app.MapPost("/api/messages", async (HttpRequest req, AIAgent a) =>
{
    // adapter.ProcessAsync(req, res, async (turnContext, ct) => {
    //   await foreach (var update in a.RunStreamingAsync(turnContext.Activity.Text, ct))
    //       await turnContext.StreamReply(update);   // streaming to Copilot
    // });
});
app.Run();
```

### 10.2 Python proxy host — forward to Foundry/MAF backend
```python
from microsoft.agents.hosting.core import ActivityHandler, TurnContext

class ProxyAgent(ActivityHandler):
    async def on_message_activity(self, turn_context: TurnContext):
        user_text = turn_context.activity.text
        reply = await call_foundry_backend(user_text)   # project endpoint + Agent Id
        await turn_context.send_activity(reply)
```

### 10.3 Connect Foundry agent (Path B inputs / Path C proxy target)
```
Project endpoint: https://<proj>-resource.services.ai.azure.com/api/projects/<proj>
Agent Id:         asst_xxxxxxxx
```

### 10.4 Manifest snippet (C4)
```json
{
  "manifestVersion": "1.22",
  "copilotAgents": { "customEngineAgents": [ { "id": "${{BOT_ID}}", "type": "bot" } ] },
  "bots": [ { "botId": "${{BOT_ID}}", "scopes": [ "personal", "team" ] } ]
}
```

### 10.5 Provisioning script (excerpt)
```bash
az provider register --namespace Microsoft.BotService
azd up        # provisions Bicep (Bot, Container App, Entra, App Insights) + deploys
```

### 10.6 Local dev tunnel
```bash
devtunnel host -p 3978 --allow-anonymous   # point Bot messaging endpoint at the tunnel
```

---

## 11. M365 deployment & governance runbook

1. Build app package with the Agents Toolkit (`manifest.json`, `m365agents.yml`, zip).
2. Register **Azure Bot Service** (automatic in Track 1; Bicep in Track 2); set messaging endpoint to `/api/messages`; enable **M365 Copilot + Teams** channels.
3. **Sideload** `appPackage.local.zip` (Teams → Apps → Manage your apps → Upload a custom app) → "Open with Copilot" to test.
4. **Org publish:** choose "People in your organization" → **M365 admin approval** in the Microsoft 365 admin center → appears under *Built by your org*. Scope to pilot group first.
5. Monitor via App Insights; iterate; expand scope.

---

## 12. Licensing (verify against live Microsoft pricing)

- **M365 Copilot license** (~$30/user/mo) required for users to consume CEAs in Copilot; it **zero-rates** Copilot Studio message consumption for those users.
- **Copilot Studio** (only if Path B/D): message **packs ($200 / 25,000 msgs / tenant / mo)** or **PAYG (~$0.01/msg)**; weights vary by action type.
- Web-grounded declarative agents can run with **no** Copilot license (not our scenario).
- Azure costs: Foundry model usage, Container App/App Service, Bot Service, App Insights.

---

## 13. Security, observability, testing

- **Security:** Managed Identity everywhere; OBO for downstream; least-privilege Entra scopes; no secrets in code (Key Vault). Note **Private Link unsupported** for Teams/Azure Bot Service (direct-publish path).
- **Observability:** OpenTelemetry → App Insights; trace turn → Foundry → tool calls; log latency, token weights, failures.
- **Testing:** unit (tools/handlers), integration (Bot emulator + dev tunnel), E2E (sideloaded package in Copilot), auth tests (OBO success/expiry), load (streaming under concurrency).

---

## 14. Risks, limitations, open questions

| Risk / limitation | Impact | Mitigation |
|---|---|---|
| Preview features shift | Rework | Re-verify status at build; keep Track 2 as durable path |
| Direct-publish gaps (no streaming/citations/file/image in Copilot) | Pilot UX | Use only for pilot; production = CEA |
| Copilot Studio connect = new Foundry portal only (classic → 404) | Blocked path | Ensure agents created in new portal |
| Foundry-published agent ≠ A2A server | A2A blocked | Host MAF externally for A2A server |
| RBAC pitfalls (Bot Contributor 403, null `agent.identity`, dev name >32) | Publish fails | Pre-flight checklist |
| Exact CS message weights uncertain | Budget | Confirm live pricing |

**Open questions:** (1) In-process MAF host vs proxy to existing Foundry project? (2) Which downstream APIs need OBO scopes? (3) Pilot user group & admin approver? (4) Region/data-residency constraints?

---

## 15. Acceptance criteria

- [ ] Track 1 pilot live in Copilot for a test user.
- [ ] Track 2 CEA responds in Copilot + Teams with streaming and citations.
- [ ] Downstream calls use OBO user token (verified in traces).
- [ ] IaC provisions all resources; CI/CD deploys end-to-end.
- [ ] Org-wide publish approved and scoped; observability dashboards live.

---

## 16. Sources (authoritative)

- Publish a Foundry agent to M365 Copilot and Teams — learn.microsoft.com/azure/ai-foundry/agents/how-to/publish-copilot (05/2026, EAP)
- Custom engine agents overview — learn.microsoft.com/microsoft-365/copilot/extensibility/overview-custom-engine-agent (06/2026)
- Build & deploy CEAs with the Agents SDK — learn.microsoft.com/microsoft-365/copilot/extensibility/create-deploy-agents-sdk (06/2026)
- M365 Agents SDK hub — learn.microsoft.com/microsoft-365/agents-sdk/ (06/2026)
- Connect to a Microsoft Foundry agent (Copilot Studio) — learn.microsoft.com/microsoft-copilot-studio/add-agent-foundry-agent (02/2026, Preview)
- Agent-to-agent (A2A) tool in Foundry — learn.microsoft.com/azure/foundry/agents/how-to/tools/agent-to-agent (06/2026, Preview)
- M365 Copilot extensibility FAQ — learn.microsoft.com/microsoft-365/copilot/extensibility/faq (06/2026)
- microsoft/Agents — AgentFrameworkWeather (.NET) — github.com/microsoft/Agents/tree/main/samples/dotnet/Agent%20Framework
- Azure-Samples/m365-custom-engine-agents (proxy pattern) — github.com/Azure-Samples/m365-custom-engine-agents
- Foundry agents as A2A servers — discussion #312 — github.com/orgs/microsoft-foundry/discussions/312
- MAF RC → GA migration — devblogs.microsoft.com/agent-framework/ (02/2026)
- Copilot Camp — Custom Engine Agents (Agents SDK labs) — microsoft.github.io/copilot-camp/pages/custom-engine/agents-sdk/

*Internal Microsoft decks corroborating the Agents SDK + Foundry path: "Azure AI Foundry" (M365 Agents SDK / Copilot Studio & Foundry), "Deep Dive into Agent Stack in Azure AI Foundry L300" (SharePoint). No prior internal PRD on this exact scenario was found.*
