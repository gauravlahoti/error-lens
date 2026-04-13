import os
from pathlib import Path
from dotenv import load_dotenv
from google.adk.artifacts import InMemoryArtifactService, GcsArtifactService

load_dotenv(Path(__file__).parent.parent / ".env")

_gcs_bucket = os.environ.get("ARTIFACT_GCS_BUCKET")

# InMemoryArtifactService for local adk web dev.
# Set ARTIFACT_GCS_BUCKET in .env or Cloud Run env vars to use durable GCS storage.
artifact_service = (
    GcsArtifactService(bucket_name=_gcs_bucket)
    if _gcs_bucket
    else InMemoryArtifactService()
)
