# Error KB Agent

A conversational agent that helps engineering teams search, record, and manage GCP error resolutions from a persistent knowledge bank. Built with [Google ADK](https://github.com/google/adk-python), backed by AlloyDB via [MCP Toolbox for Databases](https://github.com/googleapis/genai-toolbox), and exposed as a remote [A2A](https://google.github.io/A2A/) service on Cloud Run.

The agent uses ADK's **skills system** to discover workflows at runtime, with **L1 / L2 / L3 skill tiers** that separate simple lookups from guided multi-step conversations. Code-level callbacks enforce skill loading and redact internal names before they reach end users.

---

## Architecture

```text
┌─────────────────┐       A2A Protocol       ┌──────────────────┐    ToolboxToolset    ┌──────────────────┐
│  a2a_client     │ ──────────────────────▶  │  Error KB Agent  │ ────────────────── ▶ │  Error KB        │
│  (local ADK)    │   RemoteA2aAgent         │  (Cloud Run)     │   HTTP/REST          │  Toolbox         │
│                 │                           │                  │                      │  (Cloud Run)     │
│  root_agent     │                           │  ADK + to_a2a()  │                      │  MCP Toolbox     │
│  + sub_agent    │                           │  + uvicorn       │                      │  + AlloyDB       │
└─────────────────┘                           └──────────────────┘                      └──────────────────┘
```

---

## Skills System

The agent does **not** hard-code tool names in its instruction. Instead it discovers capabilities at runtime through ADK's `SkillToolset`:

1. **`list_skills`** — returns available skills with descriptions.
2. **`load_skill`** — loads a skill's `SKILL.md` which lists tools, steps, and rules.
3. **`load_skill_resource`** — loads reference guides (output format, workflow, field validation).
4. The agent follows the steps from the loaded skill and calls the corresponding tools.

### Skill Tiers — L1 / L2 / L3

Skills are grouped into three tiers based on complexity and the level of orchestration they require:

| Tier | Complexity | Turns | Skills | Description |
|------|-----------|-------|--------|-------------|
| **L1 — Lookup** | Low | Single tool call → formatted response | `search-errors`, `open-cases` | Read-only database queries that return results for the agent to format. No multi-step interaction. |
| **L2 — Guided workflow** | Medium | Multi-step with reference guides | `log-error` | Requires field validation against a reference guide before calling the tool. Agent loads the guide, validates, then executes. |
| **L3 — Conversational** | High | Multi-turn conversation with sequential tool calls | `resolve-case` | Guided multi-step flow: retrieve case details → present suggested fixes → collect engineer confirmation → deposit fix. Requires the agent to manage conversation state across turns. |

### Skill Inventory

| Skill | Tier | Tools Used | Reference Guides |
|-------|------|-----------|------------------|
| `search-errors` | L1 | `search-similar-errors` | `similarity_guide.md`, `output_style_guide.md` |
| `open-cases` | L1 | `get-open-cases` | `output_style_guide.md` |
| `log-error` | L2 | `record-new-error` | `field_guide.md` |
| `resolve-case` | L3 | `get-case-by-id`, `deposit-fix` | `workflow_guide.md` |

### Skill directory structure

```text
skills/
├── search-errors/
│   ├── SKILL.md                          # Steps, tools, rules
│   └── references/
│       ├── similarity_guide.md           # Score ranges, threshold 0.85
│       └── output_style_guide.md         # Table format, no-results handling
├── open-cases/
│   ├── SKILL.md
│   └── references/
│       └── output_style_guide.md         # Sort by severity, table format
├── log-error/
│   ├── SKILL.md
│   └── references/
│       └── field_guide.md                # 7 required fields, validation rules
└── resolve-case/
    ├── SKILL.md
    └── references/
        └── workflow_guide.md             # 4-step conversation flow
```

---

## Callbacks

Two code-level callbacks enforce agent behaviour deterministically — independent of prompt instructions:

| Callback | Type | Purpose |
|----------|------|---------|
| `_require_skill_first` | `before_tool_callback` | Blocks domain tools until a skill has been loaded. Forces the agent through `list_skills` → `load_skill` before calling any database tool. Uses a module-level flag that persists across A2A sessions. |
| `_redact_internals` | `after_model_callback` | Strips leaked internal names (skill names, tool names, callback details) from any text response before it reaches the user. Deterministic regex — the LLM cannot bypass it. |

---

## What It Does

| Capability | Tier | Description |
|------------|------|-------------|
| **Semantic search** | L1 | Search resolved cases with confirmed fixes ranked by similarity (threshold ≥ 0.85) |
| **Open case triage** | L1 | List all unresolved cases ordered by severity |
| **New error recording** | L2 | Record a newly triaged error with validated fields |
| **Case resolution** | L3 | Guided multi-step flow: retrieve case → show suggested fixes → confirm fix → deposit |
| **Embedding refresh** | — | When a fix is deposited, the case embedding is regenerated to include the resolution |

---

## Prerequisites

| Requirement | Notes |
|-------------|-------|
| Python 3.14+ | Required by `pyproject.toml` |
| [uv](https://docs.astral.sh/uv/) | Fast Python package manager |
| Google Cloud project | With Vertex AI API enabled |
| Running **Error KB Toolbox** | See [error-kb-toolbox README](../error-kb-toolbox/README.md) |
| `gcloud` CLI | Installed and authenticated |

---

## Getting Started

### 1. Clone and navigate

```bash
git clone https://github.com/gauravlahoti/error-lens.git
cd error-lens/error-kb-agent
```

### 2. Install dependencies

```bash
uv sync
```

This installs `google-adk[a2a]`, `python-dotenv`, `toolbox-adk`, and `toolbox-core` from the lockfile.

### 3. Set up environment variables

```bash
cp error_kb_agent/.env.template error_kb_agent/.env
```

Open `error_kb_agent/.env` and fill in:

| Variable | Example | Description |
|----------|---------|-------------|
| `GOOGLE_GENAI_USE_VERTEXAI` | `1` | `1` for Vertex AI, `0` for AI Studio |
| `GOOGLE_CLOUD_PROJECT` | `my-gcp-project` | Your GCP project ID |
| `GOOGLE_CLOUD_LOCATION` | `us-central1` | GCP region |
| `TOOLBOX_URL` | `https://error-kb-toolbox-xxx.run.app` | URL of your Error KB Toolbox deployment |
| `MODEL` | `gemini-2.5-flash` | Gemini model name |

### 4. Run locally with ADK Web

```bash
uv run adk web
```

Open http://localhost:8000 and select `error_kb_agent` from the agent dropdown.

> **Important:** Use `uv run adk web` (not bare `adk web`) to ensure the virtual environment with the `[a2a]` extra is active.

---

## Deploying to Cloud Run (A2A)

The agent is exposed as an A2A-compatible server using `to_a2a()` and served via `uvicorn`.

### 1. Build and deploy

```bash
gcloud run deploy error-kb-agent \
    --source . \
    --region us-central1 \
    --project <YOUR_PROJECT_ID> \
    --set-env-vars "GOOGLE_GENAI_USE_VERTEXAI=1,GOOGLE_CLOUD_PROJECT=<YOUR_PROJECT_ID>,GOOGLE_CLOUD_LOCATION=us-central1,TOOLBOX_URL=<YOUR_TOOLBOX_URL>,MODEL=gemini-2.5-flash,A2A_BASE_URL=https://error-kb-agent-<PROJECT_NUMBER>.us-central1.run.app" \
    --port=8080 \
    --allow-unauthenticated
```

> **Important:** Set `A2A_BASE_URL` to the Cloud Run service URL so the agent card advertises the correct public endpoint instead of `localhost:8080`.

### 2. Verify the agent card

```bash
curl https://<YOUR_AGENT_URL>/.well-known/agent.json
```

You should see the agent card JSON with the five tools listed as capabilities.

### Dockerfile

The included `Dockerfile` uses `python:3.14-slim` with `uv` for dependency management:

```dockerfile
FROM python:3.14-slim
WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY error_kb_agent/ error_kb_agent/
ENV PORT=8080
CMD ["uv", "run", "uvicorn", "error_kb_agent.agent:a2a_app", "--host", "0.0.0.0", "--port", "8080"]
```

---

## A2A Client (Local Orchestrator)

The `a2a_client/` directory contains a standalone local ADK agent that connects to the remote Error KB Agent via the A2A protocol. Use this to test the deployed agent interactively.

### 1. Set up environment

```bash
cp a2a_client/.env.template a2a_client/.env
```

| Variable | Example | Description |
|----------|---------|-------------|
| `GOOGLE_GENAI_USE_VERTEXAI` | `1` | `1` for Vertex AI |
| `GOOGLE_CLOUD_PROJECT` | `my-gcp-project` | Your GCP project ID |
| `GOOGLE_CLOUD_LOCATION` | `us-central1` | GCP region |
| `ERROR_KB_AGENT_URL` | `https://error-kb-agent-xxx.run.app` | Cloud Run URL of the Error KB Agent |
| `MODEL` | `gemini-2.5-flash` | Model for the local orchestrator |

### 2. Run

```bash
uv run adk web a2a_client
```

Open http://localhost:8000 and select the `root_agent`. It delegates error-related queries to the remote `error_kb_agent` via `RemoteA2aAgent`.

---

## Close-Case Flow (L3 — resolve-case skill)

When a user asks to close or resolve a case, the agent loads the `resolve-case` skill and follows a guided multi-step conversation:

1. Loads `workflow_guide.md` reference for conversation flow rules
2. Asks for the **case ID** (if not provided)
3. Calls `get-case-by-id` to retrieve the case and its `suggested_fixes`
4. Presents the suggested fixes as a **numbered list**
5. Asks the user **which fix** resolved the issue — or accepts a custom solution
6. Asks for the **fix source**: `gcp_docs`, `community`, or `internal`
7. Calls `deposit-fix` — which also **regenerates the embedding** to include the confirmed fix

Custom solutions are prefixed with `"Other solution: <description>"` for traceability.

---

## Project Structure

```text
error-kb-agent/
├── error_kb_agent/           # Agent package (deployed to Cloud Run)
│   ├── __init__.py
│   ├── agent.py              # Agent definition, callbacks, skills, A2A via to_a2a()
│   ├── tools.py              # ToolboxToolset connection
│   ├── prompts.py            # (unused — instructions are inline + skill-driven)
│   ├── skills/               # ADK skills — L1/L2/L3 workflow definitions
│   │   ├── search-errors/    # L1 — semantic similarity search
│   │   │   ├── SKILL.md
│   │   │   └── references/
│   │   │       ├── similarity_guide.md
│   │   │       └── output_style_guide.md
│   │   ├── open-cases/       # L1 — list unresolved cases
│   │   │   ├── SKILL.md
│   │   │   └── references/
│   │   │       └── output_style_guide.md
│   │   ├── log-error/        # L2 — validated error recording
│   │   │   ├── SKILL.md
│   │   │   └── references/
│   │   │       └── field_guide.md
│   │   └── resolve-case/     # L3 — guided multi-turn case closure
│   │       ├── SKILL.md
│   │       └── references/
│   │           └── workflow_guide.md
│   ├── .env                  # Environment variables (git-ignored)
│   └── .env.template         # Template with placeholders
├── a2a_client/               # Local A2A orchestrator for testing
│   ├── __init__.py
│   ├── agent.py              # RemoteA2aAgent + root_agent
│   ├── .env                  # Environment variables (git-ignored)
│   └── .env.template         # Template with placeholders
├── Dockerfile                # Container for Cloud Run deployment
├── pyproject.toml
├── uv.lock
└── README.md
```

---

## Key Files

| File | Purpose |
|------|---------|
| `error_kb_agent/agent.py` | Defines `root_agent` with the toolbox toolset, creates `a2a_app` via `to_a2a()`. Uses `A2A_BASE_URL` env var + `urlparse` to set the correct public hostname. |
| `error_kb_agent/tools.py` | Connects to MCP Toolbox via `ToolboxToolset(server_url=TOOLBOX_URL, toolset_name="error-kb-toolbox")` |
| `error_kb_agent/prompts.py` | Agent instruction covering all five tools, close-case flow, and scope boundaries |
| `a2a_client/agent.py` | Local orchestrator with `RemoteA2aAgent(use_legacy=True)` pointing at the deployed agent |

---

## Related

- [Error KB Toolbox](../error-kb-toolbox/README.md) — MCP Toolbox for Databases deployment backing this agent
- [ErrorLens MAS](../error-lens-mas/README.md) — Multi-agent pipeline that triages GCP errors and populates the knowledge bank via this agent
- [Google ADK](https://github.com/google/adk-python) — Agent Development Kit
- [A2A Protocol](https://google.github.io/A2A/) — Agent-to-Agent communication standard
