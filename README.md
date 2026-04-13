# ErrorLens

**ErrorLens** is a self-learning team knowledge system for GCP errors. Every confirmed fix makes the next engineer faster — when you resolve a case, ErrorLens regenerates its knowledge bank embedding to include the confirmed resolution, so future similar errors match instantly instead of triggering a full research pipeline.

The more your team uses it, the smarter it gets. A brand-new deployment does a full parallel research run for every error. A mature deployment skips straight to a confirmed fix for anything the team has seen before.

Under the hood it combines parallel research across GCP documentation and community sources, an AlloyDB vector knowledge bank, a skill-driven A2A agent architecture built on Google ADK, and exportable PDF diagnostic reports for team sharing.

## Key Features

- **Self-improving knowledge bank** — when a fix is confirmed, the case embedding is regenerated to include the resolution; future similar errors skip the full pipeline entirely
- **Parallel research** — searches GCP documentation (Developer Knowledge MCP) and community sources (Google Search) simultaneously
- **Confidence scoring** — ranked fixes with composite confidence from source authority, relevance, and validation (`0.4 × authority + 0.3 × relevance + 0.3 × validation`)
- **PDF diagnostic reports** — exportable consulting-grade reports with Google Material pastel design, ranked resolution playbook, and case tracking; stored in GCS for team sharing
- **Knowledge bank** — AlloyDB-backed vector store with pgvector for semantic similarity search across past incidents (threshold ≥ 0.85)
- **Skill-driven workflows** — L1 (lookups), L2 (validated writes), L3 (multi-turn conversations) discovered at runtime via ADK SkillToolset
- **Code-level safety** — `before_tool_callback` enforces skill loading order, independent of LLM behaviour
- **Case lifecycle** — record new errors, search for similar resolved cases, deposit confirmed fixes, list open cases
- **A2A communication** — error-lens-mas connects to error-kb-agent via the Agent-to-Agent protocol

## Architecture

ErrorLens is composed of three independently deployable services:

| Service | Description | Deployment |
|---------|-------------|------------|
| [error-lens-mas](error-lens-mas/) | Multi-agent orchestrator — routes errors through triage, parallel research, synthesis, case management, and PDF report generation | Cloud Run via `adk deploy cloud_run` |
| [error-kb-agent](error-kb-agent/) | A2A remote agent — manages the error knowledge bank with L1/L2/L3 skills (search, record, resolve) | Cloud Run via `gcloud run deploy --source` |
| [error-kb-toolbox](error-kb-toolbox/) | MCP Toolbox for Databases — SQL tools backed by AlloyDB with pgvector embeddings | Cloud Run via `gcloud run deploy --source` |

```text
Developer
   │
   ▼
error-lens-mas (ADK Multi-Agent System)
   │
   │  Internal orchestration:
   │  ┌─ quick_scan (SequentialAgent) ─── signal extraction → KB search
   │  ├─ sage_pipeline (SequentialAgent)
   │  │     ├─ deep_search_agent (ParallelAgent) ─── GCP docs + community search
   │  │     └─ research_aggregator → kb_record → response_presenter
   │  │           └─ generate_pdf_report (ADK Artifact → GCS bucket)
   │  └─ kb_resolve_remote (RemoteA2aAgent) ─── close/list cases via direct A2A
   │
   │  A2A Protocol
   ▼
error-kb-agent (ADK + A2A Agent + Skills)
   │  L1: search-errors, open-cases
   │  L2: log-error (validated recording)
   │  L3: resolve-case (multi-turn guided fix)
   │
   │  MCP Toolbox
   ▼
error-kb-toolbox (AlloyDB + pgvector)
```

## Quick Start

See each service's README for setup and deployment instructions:

1. **[error-kb-toolbox](error-kb-toolbox/README.md)** — Deploy the MCP Toolbox first (requires AlloyDB instance)
2. **[error-kb-agent](error-kb-agent/README.md)** — Deploy the A2A knowledge bank agent (needs toolbox URL)
3. **[error-lens-mas](error-lens-mas/README.md)** — Deploy the multi-agent orchestrator (needs KB agent URL)

## Built With

| Technology | Role |
|------------|------|
| [Google ADK](https://google.github.io/adk-docs/) | Multi-agent orchestration + skills system + ADK Artifacts |
| [Gemini 2.5](https://deepmind.google/technologies/gemini/) | LLM backbone |
| [A2A Protocol](https://google.github.io/A2A/) | Agent-to-agent communication |
| [MCP Toolbox for Databases](https://github.com/googleapis/genai-toolbox) | Database tool layer |
| [ADK Skills](https://google.github.io/adk-docs/skills/) | L1/L2/L3 runtime workflow discovery for the KB agent |
| [AlloyDB + pgvector](https://cloud.google.com/alloydb/docs/ai/work-with-embeddings) | Vector similarity search |
| [Pydantic](https://docs.pydantic.dev/) | Structured schemas for inter-agent data flow |
| [Developer Knowledge MCP](https://docs.cloud.google.com/mcp/supported-products) | GCP documentation search |
| [fpdf2](https://py-pdf.github.io/fpdf2/) | PDF report generation with Google Material pastel design |
| [Google Cloud Storage](https://cloud.google.com/storage) | Durable artifact storage for generated PDF reports |
| [Cloud Run](https://cloud.google.com/run) | Serverless deployment for all services |
