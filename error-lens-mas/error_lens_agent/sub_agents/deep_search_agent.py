"""Parallel fan-out — runs GCP docs and community research concurrently."""

from google.adk.agents import ParallelAgent

from error_lens_agent.sub_agents.gcp_knowledge_agent import gcp_knowledge_agent
from error_lens_agent.sub_agents.community_search_agent import community_search_agent

# =============================================================================
# Searches GCP docs and community sources simultaneously
# =============================================================================
deep_search_agent = ParallelAgent(
    name="deep_search_agent",
    description="Searches GCP docs and community sources simultaneously.",
    sub_agents=[gcp_knowledge_agent, community_search_agent],
)
