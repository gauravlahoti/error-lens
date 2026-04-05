"""Research aggregator — synthesises all research findings into a ranked resolution."""

from google.adk.agents import LlmAgent
from google.genai import types

from error_lens_agent.config.config import MODEL_MAX_REASONING
from error_lens_agent.models import synthesis_result
from error_lens_agent.prompts import synthesis_agent_instruction


# =============================================================================
# Aggregates GCP docs and community research into a ranked resolution
# =============================================================================
research_aggregator_agent = LlmAgent(
    name="research_aggregator_agent",
    model=MODEL_MAX_REASONING,
    description="Aggregates GCP docs and community research into a ranked resolution.",
    instruction=synthesis_agent_instruction,
    include_contents="none",
    output_schema=synthesis_result,
    output_key="synthesis_result",
)
