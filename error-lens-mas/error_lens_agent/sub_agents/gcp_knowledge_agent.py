"""Official GCP documentation research pipeline (search -> format)."""

from google.adk.agents import LlmAgent, SequentialAgent
from google.genai import types

from error_lens_agent.config.config import MAX_RESEARCH_OUTPUT_TOKENS, MODEL_FAST, MODEL_MAX_REASONING
from error_lens_agent.models import gcp_knowledge_research_result
from error_lens_agent.prompts import (
    gcp_knowledge_agent_instruction,
    gcp_knowledge_formatter_instruction,
)
from error_lens_agent.tools import gcp_developer_knowledge_toolset

# =============================================================================
# Step A - searches official GCP docs via Developer Knowledge MCP
# =============================================================================
gcp_knowledge_search_agent = LlmAgent(
    name="gcp_knowledge_search_agent",
    model=MODEL_MAX_REASONING,
    description="Searches official GCP documentation via Developer Knowledge MCP.",
    instruction=gcp_knowledge_agent_instruction,
    include_contents="none",
    tools=[gcp_developer_knowledge_toolset],
    output_key="gcp_knowledge_agent_raw",
    generate_content_config=types.GenerateContentConfig(
        max_output_tokens=MAX_RESEARCH_OUTPUT_TOKENS,
    ),
)

# =============================================================================
# Step B - structures raw documentation findings into schema output
# =============================================================================
gcp_knowledge_formatter_agent = LlmAgent(
    name="gcp_knowledge_formatter_agent",
    model=MODEL_FAST,
    description="Structures raw GCP documentation findings into gcp_knowledge_research_result.",
    instruction=gcp_knowledge_formatter_instruction,
    output_schema=gcp_knowledge_research_result,
    output_key="gcp_knowledge_agent_result",
)

# =============================================================================
# Pipeline - search then format sequentially
# =============================================================================
gcp_knowledge_agent = SequentialAgent(
    name="gcp_knowledge_agent",
    description="Searches official GCP docs and formats the results sequentially.",
    sub_agents=[gcp_knowledge_search_agent, gcp_knowledge_formatter_agent],
)
