"""
Central configuration for ErrorLens.

All environment variable reads and runtime constants live here.
Sub-agents import from this file directly — no os.environ calls elsewhere.

To override any value, set the corresponding key in your .env file.
"""

import os

from google.adk.models.lite_llm import LiteLlm 


# ── Provider switch — change this one value to swap all models ─
MODEL_PROVIDER = os.environ.get("MODEL_PROVIDER", "gemini").strip().lower()


def _get_provider_model(tier_name: str):
    model_name = os.environ.get(f"{MODEL_PROVIDER.upper()}_MODEL_{tier_name.upper()}", "")
    if MODEL_PROVIDER == "anthropic" and model_name:
        return LiteLlm(model=model_name)
    return model_name

if MODEL_PROVIDER == "anthropic":
    MODEL_MAX_REASONING = _get_provider_model("max_reasoning")
    MODEL_BALANCED      = _get_provider_model("balanced")
    MODEL_FAST          = _get_provider_model("fast")
else:
    MODEL_MAX_REASONING = _get_provider_model("max_reasoning")
    MODEL_BALANCED      = _get_provider_model("balanced")
    MODEL_FAST          = _get_provider_model("fast")

# google_search is only supported on Gemini-backed models, so keep a dedicated
# override for that tool path even when the wider pipeline uses Anthropic.
GOOGLE_SEARCH_MODEL = os.environ.get("GOOGLE_SEARCH_MODEL") or os.environ.get(
    "GEMINI_MODEL_BALANCED", "gemini-2.5-flash"
)


# ── GCP project ───────────────────────────────────────────────────────────────

GOOGLE_CLOUD_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
GOOGLE_CLOUD_REGION  = os.environ.get("GOOGLE_CLOUD_REGION",  "us-central1")


# ── MCP server endpoints ──────────────────────────────────────────────────────

DEVELOPER_KNOWLEDGE_MCP_URL = "https://developerknowledge.googleapis.com/mcp"
DEVELOPER_KNOWLEDGE_API_KEY = os.environ.get("DEVELOPER_KNOWLEDGE_API_KEY", "")


# ── Remote A2A agents ─────────────────────────────────────────────────────────

KB_AGENT_URL = os.environ.get("KB_AGENT_URL", "http://localhost:8001")
KB_SIMILARITY_THRESHOLD = float(os.environ.get("KB_SIMILARITY_THRESHOLD", "0.85"))

# ── MCP Toolbox for Databases (direct search, bypasses A2A) ──────────────────

TOOLBOX_URL = os.environ.get("TOOLBOX_URL", "")

ALLOYDB_MCP_URL = (
    f"https://alloydb.{GOOGLE_CLOUD_REGION}.rep.googleapis.com/mcp"
)

# ── LLM response budgeting ───────────────────────────────────────────────────
# Caps verbose raw search responses before formatter agents structure them.

MAX_RESEARCH_OUTPUT_TOKENS  = int(os.environ.get("MAX_RESEARCH_OUTPUT_TOKENS",  "1500"))
