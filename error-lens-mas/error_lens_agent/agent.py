from google.adk.agents import LlmAgent, SequentialAgent

from error_lens_agent.config.config import MODEL_FAST, MODEL_BALANCED, MODEL_BALANCED_NAME, MODEL_MAX_REASONING, MAX_RESEARCH_OUTPUT_TOKENS
from error_lens_agent.token_tracker import make_token_tracker

from error_lens_agent.sub_agents.signal_extractor_agent import signal_extractor_agent
from error_lens_agent.sub_agents.deep_search_agent import deep_search_agent
from error_lens_agent.sub_agents.research_aggregator_agent import research_aggregator_agent
from error_lens_agent.sub_agents.knowledge_bank_agent import kb_record_agent, kb_search_agent, kb_resolve_remote, kb_stats_toolset
from error_lens_agent.tools.report_pdf_tool import generate_pdf_report
from error_lens_agent.prompts import (
    root_agent_instruction,
    response_presenter_instruction,
)

# =============================================================================
# Final pipeline step — formats and delivers the ranked resolution to the developer
# =============================================================================
response_presenter_agent = LlmAgent(
    name="response_presenter_agent",
    model=MODEL_BALANCED,
    description="Formats synthesis_result into a clear, empathetic developer response.",
    instruction=response_presenter_instruction,
    include_contents="none",
    tools=[generate_pdf_report],
    after_model_callback=make_token_tracker(MODEL_BALANCED_NAME),
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
)

# =============================================================================
# Quick scan — extracts error context, then checks the knowledge bank
# =============================================================================
quick_scan = SequentialAgent(
    name="quick_scan",
    description="Extracts structured error context, then searches the knowledge bank for similar resolved cases.",
    sub_agents=[
        signal_extractor_agent,     # step 1 — extracts structured error context
        kb_search_agent,            # step 2 — searches KB with structured data
    ],
)

# =============================================================================
# Full research pipeline — picks up from error_triage_result already in state
# =============================================================================
sage_pipeline = SequentialAgent(
    name="sage_pipeline",
    description="Full error research pipeline — deep search, aggregate, record, present.",
    sub_agents=[
        deep_search_agent,          # step 1 — parallel research across all sources
        research_aggregator_agent,  # step 2 — aggregates findings, scores confidence
        kb_record_agent,            # step 3 — records new case in knowledge bank
        response_presenter_agent,   # step 4 — formats and delivers final response
    ],
)

# =============================================================================
# Root agent — ADK entry point
# =============================================================================
root_agent = LlmAgent(
    name="error_lens_agent",
    model=MODEL_BALANCED,
    description="ErrorLens — routes developer requests to the right agent.",
    instruction=root_agent_instruction,
    tools=[kb_stats_toolset, generate_pdf_report],
    sub_agents=[quick_scan, sage_pipeline, kb_resolve_remote],
    after_model_callback=make_token_tracker(MODEL_BALANCED_NAME),
)

