# Error KB Agent

A conversational agent that helps engineering teams search, record, and manage GCP error resolutions from a persistent knowledge bank. Built with [Google ADK](https://github.com/google/adk-python), backed by AlloyDB via [MCP Toolbox for Databases](https://github.com/googleapis/genai-toolbox), and exposed as a remote [A2A](https://google.github.io/A2A/) service on Cloud Run.

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

## What It Does

| Capability | Description |
|------------|-------------|
| **Semantic search** | Search resolved cases with confirmed fixes ranked by similarity (threshold ≥ 0.85) |
| **Case lookup** | Retrieve full case details by UUID |
| **Fix recording** | Record a confirmed fix with a guided multi-step flow |
| **Open case triage** | List all unresolved cases ordered by severity |
| **New error recording** | Record a newly triaged error when no confident match exists |
| **Embedding refresh** | When a fix is deposited, the case embedding is regenerated to include the resolution |

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

## Close-Case Flow

When a user asks to close or resolve a case, the agent follows a guided multi-step flow:

1. Asks for the **case ID** (if not provided)
2. Calls `get-case-by-id` to retrieve the case and its `suggested_fixes`
3. Presents the suggested fixes as a **numbered list**
4. Asks the user **which fix** resolved the issue — or accepts a custom solution
5. Asks for the **fix source**: `gcp_docs`, `community`, or `internal`
6. Calls `deposit-fix` — which also **regenerates the embedding** to include the confirmed fix

Custom solutions are prefixed with `"Other solution: <description>"` for traceability.

---

## Project Structure

```text
error-kb-agent/
├── error_kb_agent/           # Agent package (deployed to Cloud Run)
│   ├── __init__.py
│   ├── agent.py              # Agent definition + A2A app via to_a2a()
│   ├── tools.py              # ToolboxToolset connection
│   ├── prompts.py            # Agent instruction and behaviour rules
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
