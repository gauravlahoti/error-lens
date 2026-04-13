# Error KB Agent

A conversational agent that helps engineering teams search, record, and manage GCP error resolutions from a persistent knowledge bank. Built with [Google ADK](https://github.com/google/adk-python), backed by AlloyDB via [MCP Toolbox for Databases](https://github.com/googleapis/genai-toolbox), and exposed as a remote [A2A](https://google.github.io/A2A/) service on Cloud Run.

The agent uses ADK's **skills system** to discover workflows at runtime via **progressive disclosure** — skill names are auto-injected on every request (L1), detailed instructions are loaded on demand (L2), and reference guides provide formatting and validation rules (L3). A code-level callback enforces skill loading before any domain tool can run.

---

## What It Does

| Capability | Skill | Description |
|------------|-------|-------------|
| **Semantic search** | `search-errors` | Search resolved cases with confirmed fixes ranked by similarity (threshold ≥ 0.85) |
| **Open case triage** | `open-cases` | List all unresolved cases ordered by severity |
| **New error recording** | `log-error` | Record a newly triaged error with validated fields |
| **Case resolution** | `resolve-case` | Guided multi-step flow: retrieve case → show suggested fixes → confirm fix → deposit |
| **Embedding refresh** | _(automatic)_ | When a fix is deposited, the case embedding is regenerated to include the resolution |

---

## Architecture

```text
┌─────────────────┐       A2A Protocol       ┌──────────────────┐    ToolboxToolset    ┌──────────────────┐
│  ErrorLens MAS  │ ──────────────────────▶  │  Error KB Agent  │ ────────────────── ▶ │  Error KB        │
│  (Cloud Run)    │   RemoteA2aAgent         │  (Cloud Run)     │   HTTP/REST          │  Toolbox         │
│                 │                           │                  │                      │  (Cloud Run)     │
│  a2a_client     │                           │  ADK + to_a2a()  │                      │  MCP Toolbox     │
│  (local test)   │                           │  + uvicorn       │                      │  + AlloyDB       │
└─────────────────┘                           └──────────────────┘                      └──────────────────┘
```

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

### 1. Install uv

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 2. Clone and navigate

```bash
git clone https://github.com/gauravlahoti/error-lens.git
cd error-lens/error-kb-agent
```

### 3. Create a virtual environment and install dependencies

```bash
uv venv
uv sync
```

### 4. Authenticate with Google Cloud

```bash
gcloud auth application-default login
gcloud auth application-default set-quota-project <YOUR_PROJECT_ID>
```

### 5. Set up environment variables

```bash
cp error_kb_agent/.env.template error_kb_agent/.env
```

| Variable | Example | Description |
|----------|---------|-------------|
| `GOOGLE_GENAI_USE_VERTEXAI` | `1` | `1` for Vertex AI, `0` for AI Studio |
| `GOOGLE_CLOUD_PROJECT` | `my-gcp-project` | Your GCP project ID |
| `GOOGLE_CLOUD_LOCATION` | `us-central1` | GCP region |
| `TOOLBOX_URL` | `https://error-kb-toolbox-xxx.run.app` | URL of your Error KB Toolbox deployment |
| `MODEL` | `gemini-2.5-flash` | Gemini model name |
| `A2A_BASE_URL` | `https://error-kb-agent-xxx.run.app` | Public URL advertised in the A2A agent card |

### 6. Run locally with ADK Web

```bash
uv run adk web
```

Open http://localhost:8000 and select `error_kb_agent` from the agent dropdown.

---

## Deploying to Cloud Run (A2A)

The agent is exposed as an A2A-compatible server using `to_a2a()` and served via `uvicorn`.

### 1. Enable required APIs

```bash
gcloud services enable run.googleapis.com --project <YOUR_PROJECT_ID>
```

### 2. Build and deploy

```bash
cd error-kb-agent
gcloud run deploy error-kb-agent \
    --source . \
    --region us-central1 \
    --project <YOUR_PROJECT_ID> \
    --set-env-vars "GOOGLE_GENAI_USE_VERTEXAI=1,GOOGLE_CLOUD_PROJECT=<YOUR_PROJECT_ID>,GOOGLE_CLOUD_LOCATION=us-central1,TOOLBOX_URL=<YOUR_TOOLBOX_URL>,MODEL=gemini-2.5-flash,A2A_BASE_URL=https://error-kb-agent-<PROJECT_NUMBER>.us-central1.run.app" \
    --allow-unauthenticated
```

> **Note:** Do not pass `--port`. The Dockerfile listens on port 8080 by default and Cloud Run detects this automatically. Passing `--port 8001` causes a startup failure.

### 3. Verify the agent card

```bash
curl https://<YOUR_AGENT_URL>/.well-known/agent.json
```

### Dockerfile

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

## A2A Client (Local Test Orchestrator)

The `a2a_client/` directory contains a standalone local ADK agent that connects to the remote Error KB Agent via the A2A protocol.

```bash
cp a2a_client/.env.template a2a_client/.env
# set GOOGLE_CLOUD_PROJECT, GOOGLE_CLOUD_LOCATION, ERROR_KB_AGENT_URL, MODEL
uv run adk web a2a_client
```

---

## Skills System

The agent does **not** hard-code tool names in its instruction. Instead it discovers capabilities at runtime through ADK's `SkillToolset`:

1. **`list_skills`** — auto-injected on every LLM request. Returns skill names and descriptions. The agent does not call this explicitly.
2. **`load_skill`** — **MANDATORY first action** on every request. The agent must call this before any other tool or text response. It loads the skill's `SKILL.md` with the full workflow: tools, steps, and rules.
3. **`load_skill_resource`** — on demand. Loads reference files from a skill's `references/` directory.
4. The agent follows the steps from the loaded skill and calls the corresponding domain tools.

### Skill Tiers — L1 / L2 / L3

| Tier | Complexity | Turns | Skills | Description |
|------|-----------|-------|--------|-------------|
| **L1 — Lookup** | Low | Single tool call | `search-errors`, `open-cases` | Read-only database queries |
| **L2 — Guided workflow** | Medium | Multi-step with reference guides | `log-error` | Field validation before executing write |
| **L3 — Conversational** | High | Multi-turn conversation | `resolve-case` | Guided flow: retrieve → present → confirm → deposit |

### Skill Inventory

| Skill | Tier | Tools Used | Reference Guides |
|-------|------|-----------|------------------|
| `search-errors` | L1 | `search-similar-errors` | `similarity_guide.md`, `output_style_guide.md` |
| `open-cases` | L1 | `get-open-cases` | `output_style_guide.md` |
| `log-error` | L2 | `record-new-error` | `field_guide.md` |
| `resolve-case` | L3 | `get-case-by-id`, `deposit-fix` | `workflow_guide.md` |

---

## Callbacks

| Callback | Type | Purpose |
|----------|------|---------|
| `_require_skill_first` | `before_tool_callback` | Blocks all domain tools until `load_skill` has been called in the current session. Uses a session-state flag (`_skill_loaded`) reset per request. Enforces correct skill-first ordering independent of LLM behaviour. |

---

## Close-Case Flow (L3 — resolve-case skill)

1. Loads `workflow_guide.md` reference for conversation flow rules
2. Asks for the **case ID** (if not provided)
3. Calls `get-case-by-id` to retrieve the case and its `suggested_fixes`
4. Presents the suggested fixes as a numbered list
5. Asks which fix resolved the issue — or accepts a custom solution
6. Asks for the **fix source**: `gcp_docs`, `community`, or `internal`
7. Calls `deposit-fix` — which regenerates the embedding to include the confirmed fix

---

## Project Structure

```text
error-kb-agent/
├── error_kb_agent/
│   ├── agent.py              # root_agent, _require_skill_first callback, a2a_app via to_a2a()
│   ├── tools.py              # ToolboxToolset connection
│   ├── skills/               # ADK skills — L1/L2/L3 workflow definitions
│   │   ├── search-errors/
│   │   ├── open-cases/
│   │   ├── log-error/
│   │   └── resolve-case/
│   ├── .env                  # Environment variables (git-ignored)
│   └── .env.template
├── a2a_client/               # Local A2A orchestrator for testing
├── Dockerfile
├── pyproject.toml
└── README.md
```

---

## Related

- [Error KB Toolbox](../error-kb-toolbox/README.md) — MCP Toolbox for Databases deployment backing this agent
- [ErrorLens MAS](../error-lens-mas/README.md) — Multi-agent pipeline that triages GCP errors and populates the knowledge bank via this agent
- [Google ADK](https://github.com/google/adk-python) — Agent Development Kit
- [A2A Protocol](https://google.github.io/A2A/) — Agent-to-Agent communication standard
