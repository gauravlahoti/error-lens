# ErrorLens

**ErrorLens** is a multi-agent system that turns raw GCP errors into structured, confidence-scored diagnostic reports with ranked resolution playbooks. It combines parallel research across GCP documentation and community sources with a persistent knowledge bank of past incidents and confirmed fixes.

## Architecture

ErrorLens is composed of three independently deployable services:

| Service | Description | Deployment |
|---------|-------------|------------|
| [error-lens-mas](error-lens-mas/) | Multi-agent orchestrator — routes errors through triage, parallel research, synthesis, and case management | Cloud Run via `adk deploy cloud_run` |
| [error-kb-agent](error-kb-agent/) | A2A remote agent — manages the error knowledge bank (search, record, resolve) | Cloud Run via `gcloud run deploy --source` |
| [error-kb-toolbox](error-kb-toolbox/) | MCP Toolbox for Databases — SQL tools backed by AlloyDB with pgvector embeddings | Cloud Run via `gcloud run deploy --source` |

```text
Developer
   │
   ▼
error-lens-mas (ADK Multi-Agent System)
   │
   │  A2A Protocol
   ▼
error-kb-agent (ADK + A2A Agent)
   │
   │  MCP Toolbox
   ▼
error-kb-toolbox (AlloyDB + pgvector)
```

## Key Features

- **Parallel research** — searches GCP documentation (Developer Knowledge MCP) and community sources (Google Search) simultaneously
- **Knowledge bank** — AlloyDB-backed vector store with pgvector for semantic similarity search across past incidents
- **Case lifecycle** — record new errors, search for similar resolved cases, deposit confirmed fixes, list open cases
- **Confidence scoring** — ranked fixes with composite confidence from source authority, relevance, and validation
- **A2A communication** — error-lens-mas connects to error-kb-agent via the Agent-to-Agent protocol

## Quick Start

See each service's README for setup and deployment instructions:

1. **[error-kb-toolbox](error-kb-toolbox/README.md)** — Deploy the MCP Toolbox first (requires AlloyDB instance)
2. **[error-kb-agent](error-kb-agent/README.md)** — Deploy the A2A knowledge bank agent (needs toolbox URL)
3. **[error-lens-mas](error-lens-mas/README.md)** — Deploy the multi-agent orchestrator (needs KB agent URL)

## Built With

| Technology | Role |
|------------|------|
| [Google ADK](https://google.github.io/adk-docs/) | Multi-agent orchestration |
| [Gemini 2.5](https://deepmind.google/technologies/gemini/) | LLM backbone |
| [A2A Protocol](https://google.github.io/A2A/) | Agent-to-agent communication |
| [MCP Toolbox for Databases](https://github.com/googleapis/genai-toolbox) | Database tool layer |
| [AlloyDB + pgvector](https://cloud.google.com/alloydb/docs/ai/work-with-embeddings) | Vector similarity search |
| [Developer Knowledge MCP](https://docs.cloud.google.com/mcp/supported-products) | GCP documentation search |
| [Cloud Run](https://cloud.google.com/run) | Serverless deployment for all services |
