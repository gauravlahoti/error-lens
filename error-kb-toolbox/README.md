# Error KB Toolbox

A persistent knowledge bank for GCP error resolutions, powered by [MCP Toolbox for Databases](https://github.com/googleapis/genai-toolbox) and AlloyDB with pgvector similarity search.

Used by the **Error KB Agent** (and consumed by **ErrorLens MAS**) to store, retrieve, and confirm fixes for GCP errors encountered by engineering teams.

---

## Architecture

```text
┌──────────────┐       HTTP/REST        ┌────────────────────┐       SQL        ┌──────────────┐
│  Error KB    │ ────────────────────▶  │   MCP Toolbox for  │ ──────────────▶  │   AlloyDB    │
│  Agent (ADK) │   ToolboxToolset       │   Databases        │   pgvector +     │   (Postgres) │
└──────────────┘                        │   (Cloud Run)      │   text-embedding │              │
                                        └────────────────────┘   -005           └──────────────┘
```

---

## Tools

| Tool | Description |
|------|-------------|
| `search-similar-errors` | Semantic vector search over **resolved** cases with confirmed fixes. Only returns matches with similarity ≥ 0.85. |
| `deposit-fix` | Records a confirmed fix for an existing case, sets status to `resolved`, and **regenerates the embedding** to include the fix text. |
| `get-open-cases` | Lists all unresolved cases ordered by severity (critical → low) then creation date. |
| `get-case-by-id` | Retrieves full details for a single case by its case reference. |
| `record-new-error` | Inserts a newly triaged error as an `open` case with an auto-generated `text-embedding-005` vector (built from `error_message + error_summary + gcp_service`). |
| `get-kb-stats` | Returns resolved and open case counts. Accepts a `project_id` or `'all'` for global totals. Used by the MAS root agent on greeting. |

All tools belong to a single toolset named **`error-kb-toolbox`**.

---

## Database Schema

| Column | Type | Description |
|--------|------|-------------|
| `id` | `UUID` | Primary key, auto-generated via `gen_random_uuid()` |
| `case_ref` | `TEXT` | Human-readable case reference (e.g. `EL-20260413-00001`) |
| `error_message` | `TEXT` | Raw error message |
| `error_summary` | `TEXT` | One-sentence normalised summary |
| `gcp_service` | `TEXT` | Primary GCP service (e.g. `Cloud Run`, `BigQuery`) |
| `severity` | `TEXT` | `low`, `medium`, `high`, or `critical` |
| `status` | `TEXT` | `open` or `resolved` |
| `root_cause` | `TEXT` | Explanation of the root cause |
| `suggested_fixes` | `JSONB` | Agent-suggested fixes with confidence and source |
| `confirmed_fix` | `TEXT` | Developer-confirmed fix description |
| `fix_source` | `TEXT` | `gcp_docs`, `community`, or `internal` |
| `overall_confidence` | `FLOAT` | Confidence score (0.0–1.0) |
| `project_id` | `TEXT` | GCP project ID of the reporting team |
| `embedding` | `VECTOR(768)` | `text-embedding-005` vector for similarity search |
| `created_at` | `TIMESTAMPTZ` | Case creation timestamp |
| `resolved_at` | `TIMESTAMPTZ` | Case resolution timestamp |

---

## Prerequisites

| Requirement | Notes |
|-------------|-------|
| Google Cloud project | Billing enabled |
| AlloyDB cluster + primary instance | With public IP or Private Service Connect |
| `pgvector` extension | Available on AlloyDB by default |
| `google_ml_integration` extension | Enables in-database `embedding()` function via Vertex AI |
| [MCP Toolbox for Databases](https://github.com/googleapis/genai-toolbox) binary | v0.31.0+ for local development |
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
cd error-lens/error-kb-toolbox
```

### 3. Authenticate with Google Cloud

```bash
gcloud auth login
gcloud auth application-default login
gcloud auth application-default set-quota-project <YOUR_PROJECT_ID>
```

Enable the Vertex AI API (required for the `google_ml_integration` extension):

```bash
gcloud services enable aiplatform.googleapis.com
```

### 4. Download the toolbox binary

```bash
# macOS ARM64 example
curl -L -o toolbox \
  https://github.com/googleapis/genai-toolbox/releases/download/v0.31.0/toolbox-darwin-arm64
chmod +x toolbox
```

### 5. Set up environment variables

```bash
cp .env.template .env
```

| Variable | Example | Description |
|----------|---------|-------------|
| `PROJECT_ID` | `my-gcp-project` | Your GCP project ID |
| `REGION` | `us-central1` | GCP region |
| `CLUSTER_NAME` | `error-kb-cluster` | AlloyDB cluster name |
| `INSTANCE_NAME` | `error-kb-primary` | AlloyDB primary instance name |
| `ALLOYDB_PUBLIC_IP` | `34.x.x.x` | AlloyDB public IP address |
| `DATABASE_NAME` | `postgres` | Database name |
| `DB_USER` | `postgres` | Database user |
| `DB_PASSWORD` | — | Database password |
| `SERVICE_NAME` | `error-kb-toolbox` | Cloud Run service name |
| `IMAGE` | `us-central1-docker.pkg.dev/database-toolbox/toolbox/toolbox:latest` | Toolbox container image |

### 6. Prepare the database

Connect to your AlloyDB instance and run:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS google_ml_integration;

CREATE TABLE IF NOT EXISTS error_knowledge_bank (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    case_ref            TEXT        GENERATED ALWAYS AS (
                            'EL-' || TO_CHAR(created_at, 'YYYYMMDD') || '-' ||
                            LPAD(CAST(ROW_NUMBER() OVER (ORDER BY created_at) AS TEXT), 5, '0')
                        ) STORED,
    error_message       TEXT        NOT NULL,
    error_summary       TEXT        NOT NULL,
    gcp_service         TEXT        NOT NULL,
    severity            TEXT        NOT NULL DEFAULT 'medium',
    status              TEXT        NOT NULL DEFAULT 'open',
    root_cause          TEXT,
    suggested_fixes     JSONB,
    confirmed_fix       TEXT,
    fix_source          TEXT,
    overall_confidence  FLOAT,
    project_id          TEXT,
    embedding           VECTOR(768),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at         TIMESTAMPTZ
);
```

### 7. Run locally

> **Toolbox v0.31.0+ breaking change:** The REST API is disabled by default. Pass `--enable-api` for the UI and API endpoints to work.

```bash
source .env
./toolbox --config tools.yaml --ui --enable-api
```

Open http://127.0.0.1:5000/ui/toolsets and test tools interactively.

---

## Deploying to Cloud Run

The toolbox is deployed using a pre-built container image. `tools.yaml` is stored in Secret Manager and mounted at runtime.

### 1. Store `tools.yaml` in Secret Manager

First time:

```bash
gcloud secrets create error-kb-tools \
    --project=$PROJECT_ID \
    --data-file=tools.yaml
```

After any edit to `tools.yaml`:

```bash
gcloud secrets versions add error-kb-tools \
    --project=$PROJECT_ID \
    --data-file=tools.yaml
```

### 2. Deploy

```bash
source .env
gcloud run deploy $SERVICE_NAME \
    --image $IMAGE \
    --region $REGION \
    --project $PROJECT_ID \
    --set-secrets "/app/tools.yaml=error-kb-tools:latest" \
    --set-env-vars "PROJECT_ID=$PROJECT_ID,REGION=$REGION,CLUSTER_NAME=$CLUSTER_NAME,INSTANCE_NAME=$INSTANCE_NAME,DATABASE_NAME=$DATABASE_NAME,DB_USER=$DB_USER,DB_PASSWORD=$DB_PASSWORD,ALLOYDB_PUBLIC_IP=$ALLOYDB_PUBLIC_IP" \
    --args="--config=/app/tools.yaml,--address=0.0.0.0,--port=8080,--ui,--enable-api" \
    --port=8080 \
    --allow-unauthenticated
```

> **Important:** Do not use `--source .` — the toolbox is an image-based deployment, not a buildpack project.

### 3. Verify

```bash
curl https://<YOUR_TOOLBOX_URL>/api/toolset/error-kb-toolbox
```

---

## Known Constraints

- **`type: float` not supported** by toolbox-core's A2A agent card builder. The `overall_confidence` parameter in `record-new-error` uses `type: string` with a `$7::float` SQL cast as a workaround.
- **`tools.yaml` must not be auto-formatted** — it is a multi-document YAML (`---` separators). YAML formatters collapse the multi-document structure that MCP Toolbox requires.

---

## Project Structure

```text
error-kb-toolbox/
├── toolbox            # MCP Toolbox binary (git-ignored)
├── tools.yaml         # Source, tool, and toolset definitions (multi-document YAML)
├── pyproject.toml
├── .env               # Environment variables (git-ignored)
├── .env.template
└── README.md
```

---

## Related

- [Error KB Agent](../error-kb-agent/README.md) — ADK agent that wraps this toolbox and exposes it via A2A
- [ErrorLens MAS](../error-lens-mas/README.md) — Multi-agent pipeline that triages GCP errors and populates the knowledge bank
