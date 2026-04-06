# ErrorLens — Multi-Agent GCP Error Triage

ErrorLens is a multi-agent system (MAS) built with [Google ADK](https://google.github.io/adk-docs/) that turns raw GCP errors into structured triage, parallel research, confidence-scored synthesis, and a concise developer-facing diagnostic report.

It searches official GCP documentation through Developer Knowledge MCP, gathers community research from web search, records every case in the team's **Error Knowledge Bank** (an AlloyDB-backed vector store of past incidents and confirmed fixes) via an A2A remote agent, and delivers a ranked resolution playbook with case tracking.

---

## Architecture

```text
root_agent (LlmAgent — router)
│
├── quick_scan (SequentialAgent — fast triage + KB lookup)
│   ├── signal_extractor_agent (LlmAgent)       step 1 — extracts structured error context
│   └── kb_search_agent (LlmAgent)              step 2 — searches KB, formats results
│       └── kb_search_remote (RemoteA2aAgent)      → Error KB Agent on Cloud Run
│
├── sage_pipeline (SequentialAgent — full research pipeline)
│   ├── deep_search_agent (ParallelAgent)       step 1 — concurrent research
│   │   ├── gcp_knowledge_agent (SequentialAgent)    GCP docs MCP search → formatter
│   │   └── community_search_agent (SequentialAgent) web search → formatter
│   ├── research_aggregator_agent (LlmAgent)    step 2 — synthesises ranked fixes
│   ├── kb_record_agent (LlmAgent)              step 3 — records case, outputs case ID
│   │   └── kb_record_remote (RemoteA2aAgent)      → Error KB Agent on Cloud Run
│   └── response_presenter_agent (LlmAgent)     step 4 — formats final diagnostic report
│
└── kb_resolve_agent (LlmAgent)    resolves existing cases with confirmed fixes
    └── kb_resolve_remote (RemoteA2aAgent)         → Error KB Agent on Cloud Run
```

---

## Routing Logic

The `root_agent` handles greetings directly and classifies error-related messages:

| Intent | Route | Description |
|--------|-------|-------------|
| **General / greeting** | `root_agent` (self) | Welcomes the developer, explains capabilities, asks for error details |
| **New error** | `quick_scan` → `sage_pipeline` | Extracts structured error context, then searches the knowledge bank. If a confident match (similarity ≥ 0.85) returns, presents it with follow-up options. If no match or the developer wants deeper investigation, routes to the full pipeline. |
| **Resolve a case** | `kb_resolve_agent` | Developer has a case ID and a confirmed fix — deposits the fix into the knowledge bank |

---

## Agent Inventory

| Agent | Type | Role |
|-------|------|------|
| `root_agent` | `LlmAgent` | Handles greetings, routes to `quick_scan`, `sage_pipeline`, or `kb_resolve_agent` |
| `quick_scan` | `SequentialAgent` | Extracts error context → searches knowledge bank (signal extractor + KB search) |
| `signal_extractor_agent` | `LlmAgent` | Parses raw error into `error_triage_result` structured output |
| `kb_search_agent` | `LlmAgent` | Formats KB search results and presents follow-up options |
| `kb_search_remote` | `RemoteA2aAgent` | A2A connection to Error KB Agent for searching |
| `sage_pipeline` | `SequentialAgent` | Full research pipeline: deep search → aggregate → record → present |
| `gcp_knowledge_agent` | `SequentialAgent` | Queries Developer Knowledge MCP then formats into `gcp_knowledge_research_result` |
| `community_search_agent` | `SequentialAgent` | Runs web search then formats into `community_research_result` |
| `deep_search_agent` | `ParallelAgent` | Runs GCP docs and community search concurrently |
| `research_aggregator_agent` | `LlmAgent` | Aggregates research, ranks fixes, produces `synthesis_result` |
| `kb_record_agent` | `LlmAgent` | Records the triaged error in the knowledge bank, outputs `kb_record_result` with case ID |
| `kb_record_remote` | `RemoteA2aAgent` | A2A connection to Error KB Agent for recording |
| `response_presenter_agent` | `LlmAgent` | Formats the final developer-facing diagnostic report with case tracking |
| `kb_resolve_agent` | `LlmAgent` | Collects case ID + confirmed fix, deposits into knowledge bank via `kb_resolve_remote` |
| `kb_resolve_remote` | `RemoteA2aAgent` | A2A connection to Error KB Agent for depositing fixes |

---

## ADK Patterns Used

| Pattern | Where | Why |
|---------|-------|-----|
| `SequentialAgent` | `sage_pipeline`, `community_search_agent`, `gcp_knowledge_agent` | Preserves required execution order |
| `ParallelAgent` | `deep_search_agent` | Reduces latency by researching multiple sources concurrently |
| `RemoteA2aAgent` | `kb_search_remote`, `kb_record_remote`, `kb_resolve_remote` | Connects to the Error KB Agent on Cloud Run via A2A protocol |
| `LlmAgent` wrapper | `kb_search_agent`, `kb_record_agent`, `kb_resolve_agent` | Wraps remote agents to add formatting, structured output, and transfer control |
| `include_contents="none"` | `kb_search_agent`, `response_presenter_agent`, `research_aggregator_agent` | Forces the LLM to reformat sub-agent output rather than echoing it |
| `output_schema` | Signal extractor, formatters, aggregator, KB recorder | Enforces Pydantic models for structured inter-agent data flow |
| `output_key` | All schema-producing agents | Writes structured output to session state for downstream agents |
| `disallow_transfer_to_*` | All pipeline agents + KB search and record agents | Prevents early bailout — agents must complete their full formatted response before returning |

---

## Structured Output Models

| Model | Produced By | Consumed By |
|-------|-------------|-------------|
| `error_triage_result` | `signal_extractor_agent` | All downstream pipeline agents |
| `gcp_knowledge_research_result` | `gcp_knowledge_formatter_agent` | `research_aggregator_agent` |
| `community_research_result` | `web_search_formatter` | `research_aggregator_agent` |
| `synthesis_result` | `research_aggregator_agent` | `kb_record_agent`, `response_presenter_agent` |
| `kb_record_result` | `kb_record_agent` | `response_presenter_agent` (case ID in the report) |
All models are defined in `error_lens_agent/models.py`.

---

## Integrations

| Integration | Endpoint | Used By |
|-------------|----------|---------|
| Developer Knowledge MCP | `https://developerknowledge.googleapis.com/mcp` | `gcp_knowledge_search_agent` |
| Google built-in search | ADK built-in `google_search` tool | `web_search_agent` |
| Error KB Agent (A2A) | Configured via `KB_AGENT_URL` env var | `kb_search_remote`, `kb_record_remote`, `kb_resolve_remote` |

---

## Prerequisites

| Requirement | Notes |
|-------------|-------|
| Python 3.14+ | Required by `pyproject.toml` |
| [uv](https://docs.astral.sh/uv/) | Fast Python package manager |
| Google AI Studio API key | For Gemini model access (or Vertex AI credentials) |
| Google Cloud project | For Developer Knowledge MCP and GCP auth |
| Running **Error KB Agent** | Deployed on Cloud Run — see [error-kb-agent README](../error-kb-agent/README.md) |
| `gcloud` CLI | For authentication and enabling APIs |

### Required GCP API

```bash
gcloud services enable discoveryengine.googleapis.com
```

---

## Getting Started

### 1. Clone and navigate

```bash
git clone https://github.com/gauravlahoti/error-lens.git
cd error-lens/error-lens-mas
```

### 2. Install dependencies

```bash
uv sync
```

This installs `google-adk[a2a,extensions]` and `python-dotenv` from the lockfile.

### 3. Set up environment variables

```bash
cp error_lens_agent/.env.template error_lens_agent/.env
```

Open `error_lens_agent/.env` and fill in:

| Variable | Example | Description |
|----------|---------|-------------|
| `GOOGLE_GENAI_USE_VERTEXAI` | `0` | `0` for AI Studio, `1` for Vertex AI |
| `GOOGLE_API_KEY` | `AIza...` | Google AI Studio API key |
| `GOOGLE_CLOUD_PROJECT` | `my-gcp-project` | Your GCP project ID |
| `GOOGLE_CLOUD_REGION` | `us-central1` | GCP region |
| `DEVELOPER_KNOWLEDGE_API_KEY` | `AIza...` | API key for Developer Knowledge MCP |
| `KB_AGENT_URL` | `https://error-kb-agent-xxx.run.app` | URL of the deployed Error KB Agent |
| `GEMINI_MODEL_MAX_REASONING` | `gemini-2.5-flash` | Model for deep reasoning (aggregator) |
| `GEMINI_MODEL_BALANCED` | `gemini-2.5-flash` | Model for balanced tasks (root, presenter, all KB agents) |
| `GEMINI_MODEL_FAST` | `gemini-2.5-flash-lite` | Model for fast tasks (signal extractor, research formatters) |
| `GOOGLE_SEARCH_MODEL` | `gemini-2.5-flash` | Model for the `google_search` tool path |

**Optional — Anthropic provider:**

| Variable | Description |
|----------|-------------|
| `MODEL_PROVIDER` | Set to `anthropic` to switch all model tiers |
| `ANTHROPIC_API_KEY` | Your Anthropic API key |
| `ANTHROPIC_MODEL_MAX_REASONING` | Claude model for deep reasoning |
| `ANTHROPIC_MODEL_BALANCED` | Claude model for balanced tasks |
| `ANTHROPIC_MODEL_FAST` | Claude model for fast tasks |

> `google_search` always uses a Gemini model regardless of provider, since it is a Google-only tool.

### 4. Authenticate with Google Cloud (optional)

If you use local ADC-backed Google Cloud calls:

```bash
gcloud auth application-default login
gcloud auth application-default set-quota-project <your-project-id>
```

If using Google AI Studio (`GOOGLE_GENAI_USE_VERTEXAI=0`), the `GOOGLE_API_KEY` is the primary credential.

---

## Running Locally

### ADK Web UI

```bash
uv run adk web
```

Open http://localhost:8000 and select `error_lens_agent` from the dropdown.

> **Important:** Use `uv run adk web` (not bare `adk web`) to ensure the virtual environment with the `[a2a]` extra is active.

### CLI

```bash
uv run adk run .
```

---

## Example Interaction

**Developer submits:**

```text
Getting this on Cloud Run — please help
RESOURCE_EXHAUSTED: Quota exceeded for quota metric
'run.googleapis.com/requests' and limit 'REQUESTS_PER_MINUTE_PER_REGION'
```

**Pipeline flow:**

1. **root_agent** classifies as a new error → routes to `quick_scan`
2. **signal_extractor_agent** extracts structured `error_triage_result` with service, severity, search queries
3. **kb_search_agent** delegates to `kb_search_remote` → searches the knowledge bank
4. **kb_search_agent** formats the result with follow-up options (apply fix / run full investigation / resolve a case)
5. Developer picks **"Run a full investigation"** → `root_agent` routes to `sage_pipeline`
6. **deep_search_agent** runs GCP docs + community search in parallel
7. **research_aggregator_agent** synthesises findings into ranked `synthesis_result`
8. **kb_record_agent** delegates to `kb_record_remote` → records the case → returns `kb_record_result` with case ID
9. **response_presenter_agent** formats the final diagnostic report including the case ID for tracking

**Response includes:**
- Root cause explanation
- Ranked resolution playbook with confidence scores and source links
- Step-by-step remediation guide
- Escalation path
- Case tracking section with the knowledge bank case ID

---

## Configuration Reference

All runtime constants live in `error_lens_agent/config/config.py` and are overridden via `.env`.

| Variable | Default | Description |
|----------|---------|-------------|
| `MODEL_PROVIDER` | `gemini` | Provider switch: `gemini` or `anthropic` |
| `GEMINI_MODEL_MAX_REASONING` | — | Gemini model for deep reasoning |
| `GEMINI_MODEL_BALANCED` | — | Gemini model for balanced tasks (root, presenter, all KB agents) |
| `GEMINI_MODEL_FAST` | — | Gemini model for fast/lightweight tasks (signal extractor, research formatters) |
| `GOOGLE_SEARCH_MODEL` | `gemini-2.5-flash` | Dedicated model for `google_search` tool |
| `GOOGLE_CLOUD_REGION` | `us-central1` | GCP region |
| `DEVELOPER_KNOWLEDGE_API_KEY` | `""` | Auth for Developer Knowledge MCP |
| `GOOGLE_API_KEY` | `""` | Gemini access via Google AI Studio |
| `KB_AGENT_URL` | `http://localhost:8001` | URL of the Error KB Agent (A2A) |
| `KB_SIMILARITY_THRESHOLD` | `0.85` | Minimum similarity for a knowledge bank match to be considered confident |
| `MAX_RESEARCH_OUTPUT_TOKENS` | `1500` | Token cap for raw research responses before formatting |

---

## Project Structure

```text
error-lens-mas/
│
├── error_lens_agent/
│   ├── __init__.py
│   ├── agent.py                 # Root agent, quick_scan, sage_pipeline, presenter
│   ├── models.py                # Pydantic output schemas
│   ├── prompts.py               # All agent instructions
│   ├── .env                     # Environment variables (git-ignored)
│   ├── .env.template            # Template with placeholders
│   ├── config/
│   │   ├── __init__.py
│   │   └── config.py            # Central config — models, endpoints, thresholds
│   ├── tools/
│   │   ├── __init__.py
│   │   └── mcp_config.py        # MCP tool connections (Developer Knowledge)
│   └── sub_agents/
│       ├── __init__.py
│       ├── signal_extractor_agent.py
│       ├── deep_search_agent.py
│       ├── gcp_knowledge_agent.py
│       ├── community_search_agent.py
│       ├── research_aggregator_agent.py
│       └── knowledge_bank_agent.py   # KB search + record + resolve (LlmAgent → RemoteA2aAgent)
├── pyproject.toml
├── uv.lock
└── README.md
```

---

## Built With

| Technology | Role |
|------------|------|
| [Google ADK](https://google.github.io/adk-docs/) | Multi-agent orchestration framework |
| [Gemini 2.5](https://deepmind.google/technologies/gemini/) | LLM backbone across the pipeline |
| [Developer Knowledge MCP](https://docs.cloud.google.com/mcp/supported-products) | Official GCP documentation search |
| [A2A Protocol](https://google.github.io/A2A/) | Agent-to-agent communication with Error KB Agent |
| [Pydantic](https://docs.pydantic.dev/) | Structured schemas for inter-agent data flow |
| [AlloyDB + pgvector](https://cloud.google.com/alloydb/docs/ai/work-with-embeddings) | Vector similarity search for the knowledge bank (via Error KB Toolbox) |

---

## Related

- [Error KB Agent](../error-kb-agent/README.md) — A2A remote agent that manages the error knowledge bank
- [Error KB Toolbox](../error-kb-toolbox/README.md) — MCP Toolbox for Databases deployment backing the knowledge bank
- [Google ADK](https://google.github.io/adk-docs/) — Agent Development Kit
- [A2A Protocol](https://google.github.io/A2A/) — Agent-to-Agent communication standard
