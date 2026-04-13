# ErrorLens — Multi-Agent GCP Error Triage

ErrorLens is a multi-agent system (MAS) built with [Google ADK](https://google.github.io/adk-docs/) that turns raw GCP errors into structured triage, parallel research, confidence-scored synthesis, a concise developer-facing diagnostic report, and an exportable PDF for team sharing.

It searches official GCP documentation through Developer Knowledge MCP, gathers community research from web search, records every case in the team's **Error Knowledge Bank** (an AlloyDB-backed vector store of past incidents and confirmed fixes) via an A2A remote agent, and delivers a ranked resolution playbook with case tracking. When the investigation is complete, the developer can request a consulting-grade PDF report saved as an ADK Artifact and stored in Google Cloud Storage.

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
3. **kb_search_agent** searches the knowledge bank directly via ToolboxToolset
4. **kb_search_agent** formats the result with follow-up options (apply fix / run full investigation / resolve a case)
5. Developer picks **"Run a full investigation"** → `root_agent` routes to `sage_pipeline`
6. **deep_search_agent** runs GCP docs + community search in parallel
7. **research_aggregator_agent** synthesises findings into ranked `synthesis_result`
8. **kb_record_pipeline** runs three steps: `kb_record_input_agent` extracts all required fields into a validated Pydantic record → `kb_record_caller_agent` transfers it to `kb_record_remote` → `kb_record_formatter_agent` extracts the returned case ID into `kb_record_result`
9. **response_presenter_agent** formats the final diagnostic report including case ID and a PDF offer

**Developer says "generate PDF"** → `generate_pdf_report` saves a consulting-grade PDF as an ADK Artifact to GCS; a download link appears in the chat.

**Response includes:**
- Root cause explanation
- Ranked resolution playbook with confidence scores and source links
- Step-by-step remediation guide
- Escalation path
- Case tracking section with the knowledge bank case ID
- Optional: downloadable PDF report stored in GCS

---

## Architecture

```text
root_agent (LlmAgent — router)
│
├── quick_scan (SequentialAgent — fast triage + KB lookup)
│   ├── signal_extractor_agent (LlmAgent)       step 1 — extracts structured error context
│   └── kb_search_agent (LlmAgent)              step 2 — searches KB directly, formats results
│
├── sage_pipeline (SequentialAgent — full research pipeline)
│   ├── deep_search_agent (ParallelAgent)       step 1 — concurrent research
│   │   ├── gcp_knowledge_agent (SequentialAgent)    GCP docs MCP search → formatter
│   │   └── community_search_agent (SequentialAgent) web search → formatter
│   ├── research_aggregator_agent (LlmAgent)    step 2 — synthesises ranked fixes
│   ├── kb_record_pipeline (SequentialAgent)    step 3 — records case, outputs case ID
│   │   ├── kb_record_input_agent (LlmAgent)       3a — extracts fields → kb_record_input schema
│   │   ├── kb_record_caller_agent (LlmAgent)       3b — transfers to A2A remote
│   │   │   └── kb_record_remote (RemoteA2aAgent)      → Error KB Agent on Cloud Run
│   │   └── kb_record_formatter_agent (LlmAgent)   3c — extracts case_ref → kb_record_result
│   └── response_presenter_agent (LlmAgent)     step 4 — formats diagnostic report
│       └── generate_pdf_report (tool)              → ADK Artifact saved to GCS
│
└── kb_resolve_remote (RemoteA2aAgent)    resolves/lists cases via direct A2A transfer
       → Error KB Agent on Cloud Run (uses L1/L3 skills internally)
```

---

## Routing Logic

The `root_agent` handles greetings directly and classifies error-related messages:

| Intent | Route | Description |
|--------|-------|-------------|
| **General / greeting** | `root_agent` (self) | Welcomes the developer, explains capabilities, shows KB stats |
| **New error** | `quick_scan` → `sage_pipeline` | Extracts structured error context, then searches the knowledge bank. If a confident match (similarity ≥ 0.85) returns, presents it with follow-up options. If no match or the developer wants deeper investigation, routes to the full pipeline. |
| **Resolve a case** | `kb_resolve_remote` | Developer has a case ID and a confirmed fix — transfers directly to the KB agent which handles the multi-turn resolution via its L3 resolve-case skill |
| **PDF request** | `generate_pdf_report` (tool) | Any phrasing ("pdf", "download", "export") triggers the tool on either `root_agent` or `response_presenter_agent` |

---

## ADK Artifacts — PDF Report Export

When a full investigation completes, the developer can request a PDF:

```
Developer: "generate PDF"
→ generate_pdf_report tool reads synthesis_result, error_triage_result,
  kb_record_result from ADK session state
→ builds a consulting-grade PDF (Google Material pastel design)
→ saves it via tool_context.save_artifact() as an ADK Artifact
→ ADK writes the bytes to GCS bucket (error-lens-pdf-reports)
→ a download link appears in the ADK web UI automatically
```

**Public URL pattern:**
```
https://storage.googleapis.com/error-lens-pdf-reports/<ErrorLens_Diagnostic_Report_YYYYMMDD_HHMMSS.pdf>
```

The `artifact_service` is configured in `config/artifact_service.py` and re-exported from `__init__.py` so ADK discovers it:
- **Local dev** (`ARTIFACT_GCS_BUCKET` unset): uses `InMemoryArtifactService`
- **Cloud Run** (`ARTIFACT_GCS_BUCKET=error-lens-pdf-reports`): uses `GcsArtifactService`

**PDF quality:** The report strips all markdown formatting (bold markers, backticks, fenced code blocks) before rendering. Shell commands (`gcloud`, `kubectl`, `export`, etc.) are automatically detected in step text and rendered as dark monospace code blocks with green text — matching consulting-grade report standards. The artifact is saved with `Blob.display_name` set so the ADK web UI chat button shows the correct timestamped filename instead of "application.pdf".

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

### 1. Install uv

`uv` is the package manager used across this project. Skip this step if you already have it.

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

```bash
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Verify:

```bash
uv --version
```

### 2. Clone and navigate

```bash
git clone https://github.com/gauravlahoti/error-lens.git
cd error-lens/error-lens-mas
```

### 3. Create a virtual environment and install dependencies

```bash
uv venv
uv sync
```

`uv sync` reads `pyproject.toml` and `uv.lock` and installs all pinned dependencies — including `google-adk[a2a,extensions]`, `python-dotenv`, and `fpdf2` — into the local `.venv`.

### 4. Set up environment variables

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
| `TOOLBOX_URL` | `https://error-kb-toolbox-xxx.run.app` | URL of the deployed Error KB Toolbox |
| `GEMINI_MODEL_MAX_REASONING` | `gemini-2.5-flash` | Model for deep reasoning (aggregator) |
| `GEMINI_MODEL_BALANCED` | `gemini-2.5-flash` | Model for balanced tasks (root, presenter, KB agents) |
| `GEMINI_MODEL_FAST` | `gemini-2.5-flash-lite` | Model for fast tasks (signal extractor, research formatters) |
| `GOOGLE_SEARCH_MODEL` | `gemini-2.5-flash` | Model for the `google_search` tool path |
| `ARTIFACT_GCS_BUCKET` | `error-lens-pdf-reports` | GCS bucket for PDF report artifacts (leave unset to use in-memory for local dev) |

**Optional — Anthropic provider:**

| Variable | Description |
|----------|-------------|
| `MODEL_PROVIDER` | Set to `anthropic` to switch all model tiers |
| `ANTHROPIC_API_KEY` | Your Anthropic API key |
| `ANTHROPIC_MODEL_MAX_REASONING` | Claude model for deep reasoning |
| `ANTHROPIC_MODEL_BALANCED` | Claude model for balanced tasks |
| `ANTHROPIC_MODEL_FAST` | Claude model for fast tasks |

> `google_search` always uses a Gemini model regardless of provider.

### 5. Authenticate with Google Cloud

```bash
gcloud auth application-default login
gcloud auth application-default set-quota-project <your-project-id>
```

---

## Running Locally

```bash
uv run adk web
```

Open http://localhost:8000 and select `error_lens_agent` from the dropdown.

> **Important:** Use `uv run adk web` (not bare `adk web`) to ensure the virtual environment with the `[a2a]` extra is active.

---

## Deploying to Cloud Run

```bash
cd error-lens-mas
uv run adk deploy cloud_run \
    --project <YOUR_PROJECT_ID> \
    --region us-central1 \
    --service_name error-lens-mas \
    --with_ui error_lens_agent \
    -- \
    --set-env-vars "GOOGLE_GENAI_USE_VERTEXAI=1,GOOGLE_CLOUD_PROJECT=<YOUR_PROJECT_ID>,GOOGLE_CLOUD_REGION=us-central1,GOOGLE_API_KEY=<YOUR_KEY>,DEVELOPER_KNOWLEDGE_API_KEY=<YOUR_KEY>,MODEL_PROVIDER=gemini,GEMINI_MODEL_MAX_REASONING=gemini-2.5-flash,GEMINI_MODEL_BALANCED=gemini-2.5-flash,GEMINI_MODEL_FAST=gemini-2.5-flash-lite,GOOGLE_SEARCH_MODEL=gemini-2.5-flash,KB_AGENT_URL=<YOUR_KB_AGENT_URL>,TOOLBOX_URL=<YOUR_TOOLBOX_URL>,KB_SIMILARITY_THRESHOLD=0.85,ARTIFACT_GCS_BUCKET=error-lens-pdf-reports" \
    --allow-unauthenticated
```

> **Note:** The package directory (`error_lens_agent`) must be the last positional argument before `--`. Passing `.` instead breaks the import path on Cloud Run.

Verify:

```bash
curl https://<YOUR_MAS_URL>/.well-known/agent.json
```

---

## Agent Inventory

| Agent / Tool | Type | Role |
|---|---|---|
| `root_agent` | `LlmAgent` | Handles greetings, shows KB stats, routes to `quick_scan`, `sage_pipeline`, or `kb_resolve_remote` |
| `quick_scan` | `SequentialAgent` | Extracts error context → searches knowledge bank |
| `signal_extractor_agent` | `LlmAgent` | Parses raw error into `error_triage_result` structured output |
| `kb_search_agent` | `LlmAgent` | Searches KB directly via ToolboxToolset, formats results with follow-up options |
| `sage_pipeline` | `SequentialAgent` | Full research pipeline: deep search → aggregate → record → present |
| `gcp_knowledge_agent` | `SequentialAgent` | Queries Developer Knowledge MCP then formats into `gcp_knowledge_research_result` |
| `community_search_agent` | `SequentialAgent` | Runs web search then formats into `community_research_result` |
| `deep_search_agent` | `ParallelAgent` | Runs GCP docs and community search concurrently |
| `research_aggregator_agent` | `LlmAgent` | Aggregates research, ranks fixes, produces `synthesis_result` |
| `kb_record_pipeline` | `SequentialAgent` | Three-step pipeline: extract fields → call A2A → structure case ref |
| `kb_record_input_agent` | `LlmAgent` | Reads `error_triage_result` + `synthesis_result` from state; produces validated `kb_record_input` Pydantic record (all 8 required fields including `project_id`) |
| `kb_record_caller_agent` | `LlmAgent` | Reads `kb_record_input` from state; transfers to `kb_record_remote`; writes raw A2A response to `kb_record_raw_response` |
| `kb_record_remote` | `RemoteA2aAgent` | A2A connection to Error KB Agent for recording (triggers L2 log-error skill) |
| `kb_record_formatter_agent` | `LlmAgent` | Extracts `EL-YYYYMMDD-NNNNN` case ref from `kb_record_raw_response`; produces `kb_record_result` |
| `response_presenter_agent` | `LlmAgent` | Formats the final developer-facing diagnostic report with case tracking |
| `kb_resolve_remote` | `RemoteA2aAgent` | Direct A2A transfer to Error KB Agent for case resolution and open case listing |
| `generate_pdf_report` | Tool (async function) | Builds consulting-grade PDF from session state, saves as ADK Artifact to GCS |

---

## ADK Patterns Used

| Pattern | Where | Why |
|---------|-------|-----|
| `SequentialAgent` | `sage_pipeline`, `kb_record_pipeline`, `community_search_agent`, `gcp_knowledge_agent` | Preserves required execution order |
| `ParallelAgent` | `deep_search_agent` | Reduces latency by researching multiple sources concurrently |
| `RemoteA2aAgent` | `kb_record_remote`, `kb_resolve_remote` | Connects to the Error KB Agent on Cloud Run via A2A protocol |
| output_schema / sub_agents split | `kb_record_pipeline`, `community_search_agent` | Gemini cannot use `output_schema` and function-calling tools (including `transfer_to_agent`) in the same agent turn. Solution: separate formatting steps (no tools, `output_schema` safe) from action steps (tools, no `output_schema`). |
| `include_contents="none"` | All pipeline sub-agents | Forces agents to read only from ADK state keys, not full conversation history — reduces token usage |
| `output_schema` | Signal extractor, formatters, aggregator, KB input/formatter agents | Enforces Pydantic models for structured inter-agent data flow |
| `output_key` | All schema-producing agents | Writes structured output to session state for downstream agents |
| `disallow_transfer_to_*` | All pipeline agents + KB search/record agents | Prevents early bailout — agents must complete their full response before returning |
| ADK Artifacts | `generate_pdf_report` tool | Saves PDF bytes to GCS via `tool_context.save_artifact()` with `Blob.display_name` set; ADK web UI renders a correctly-named download link automatically |

---

## Structured Output Models

| Model | Produced By | Consumed By |
|-------|-------------|-------------|
| `error_triage_result` | `signal_extractor_agent` | All downstream pipeline agents |
| `gcp_knowledge_research_result` | `gcp_knowledge_formatter_agent` | `research_aggregator_agent` |
| `community_research_result` | `web_search_formatter` | `research_aggregator_agent` |
| `synthesis_result` | `research_aggregator_agent` | `kb_record_input_agent`, `response_presenter_agent`, `generate_pdf_report` |
| `kb_record_input` | `kb_record_input_agent` | `kb_record_caller_agent` — validated record with all 8 fields required by the KB agent |
| `kb_record_result` | `kb_record_formatter_agent` | `response_presenter_agent`, `generate_pdf_report` (case ref) |

All models are defined in `error_lens_agent/models.py`.

---

## Project Structure

```text
error-lens-mas/
│
├── error_lens_agent/
│   ├── __init__.py              # Re-exports root_agent and artifact_service for ADK discovery
│   ├── agent.py                 # Root agent, quick_scan, sage_pipeline, response_presenter
│   ├── models.py                # Pydantic output schemas
│   ├── prompts.py               # All agent instructions
│   ├── token_tracker.py         # after_model_callback for token/cost tracking
│   ├── .env                     # Environment variables (git-ignored)
│   ├── .env.template            # Template with placeholders
│   ├── config/
│   │   ├── config.py            # Central config — models, endpoints, thresholds
│   │   └── artifact_service.py  # ArtifactService instance (InMemory locally, GCS on Cloud Run)
│   ├── tools/
│   │   ├── mcp_config.py        # Developer Knowledge MCP tool connection
│   │   └── report_pdf_tool.py   # generate_pdf_report — builds PDF, saves as ADK Artifact
│   └── sub_agents/
│       ├── signal_extractor_agent.py
│       ├── deep_search_agent.py
│       ├── gcp_knowledge_agent.py
│       ├── community_search_agent.py
│       ├── research_aggregator_agent.py
│       └── knowledge_bank_agent.py   # KB search + record + resolve
├── pyproject.toml
├── uv.lock
└── README.md
```

---

## Built With

| Technology | Role |
|------------|------|
| [Google ADK](https://google.github.io/adk-docs/) | Multi-agent orchestration framework + ADK Artifacts |
| [Gemini 2.5](https://deepmind.google/technologies/gemini/) | LLM backbone across the pipeline |
| [Developer Knowledge MCP](https://docs.cloud.google.com/mcp/supported-products) | Official GCP documentation search |
| [A2A Protocol](https://google.github.io/A2A/) | Agent-to-agent communication with Error KB Agent |
| [Pydantic](https://docs.pydantic.dev/) | Structured schemas for inter-agent data flow |
| [fpdf2](https://py-pdf.github.io/fpdf2/) | PDF report generation with Google Material pastel design |
| [Google Cloud Storage](https://cloud.google.com/storage) | Durable artifact storage for generated reports |
| [AlloyDB + pgvector](https://cloud.google.com/alloydb/docs/ai/work-with-embeddings) | Vector similarity search for the knowledge bank |

---

## Related

- [Error KB Agent](../error-kb-agent/README.md) — A2A remote agent that manages the error knowledge bank
- [Error KB Toolbox](../error-kb-toolbox/README.md) — MCP Toolbox for Databases deployment backing the knowledge bank
- [Google ADK](https://google.github.io/adk-docs/) — Agent Development Kit
- [A2A Protocol](https://google.github.io/A2A/) — Agent-to-Agent communication standard
