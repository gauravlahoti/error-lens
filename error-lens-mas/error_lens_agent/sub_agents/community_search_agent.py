"""Community search agent — searches the web then structures results."""

from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.tools import google_search
from google.genai import types

from error_lens_agent.config.config import (
    MODEL_BALANCED,
    MODEL_FAST,
    GOOGLE_SEARCH_MODEL,
    MAX_RESEARCH_OUTPUT_TOKENS,
)
from error_lens_agent.models import community_research_result
from error_lens_agent.prompts import (
    web_search_agent_instruction,
    web_search_formatter_instruction,
)

# ── Step A: web search — no output_schema, google_search conflict avoided ────
web_search_agent = LlmAgent(
    name="web_search_agent",
    model=GOOGLE_SEARCH_MODEL,
    description=(
        "Searches Stack Overflow, Reddit, and GitHub Issues for community solutions. "
        "Split from formatter because google_search and output_schema cannot coexist."
    ),
    instruction=web_search_agent_instruction,
    tools=[google_search],
    output_key="web_search_agent_raw",
    include_contents="none",
)

# ── Step B: structures raw search output into community_research_result ───────
web_search_formatter = LlmAgent(
    name="web_search_formatter",
    model=MODEL_FAST,
    description="Structures raw web search output into community_research_result.",
    instruction=web_search_formatter_instruction,
    output_schema=community_research_result,
    output_key="community_research_agent_result",
    include_contents="none",
)

# ── community_search_agent: search → format sequentially ─────────────────────
community_search_agent = SequentialAgent(
    name="community_search_agent",
    description="Searches community sources then structures findings sequentially.",
    sub_agents=[web_search_agent, web_search_formatter],
)