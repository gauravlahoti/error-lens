"""Step 1 of the triage pipeline — classifies intent and extracts error context."""

from google.adk.agents import LlmAgent

from error_lens_agent.config.config import MODEL_FAST, MODEL_FAST_NAME
from error_lens_agent.models import error_triage_result
from error_lens_agent.prompts import signal_extractor_instruction
from error_lens_agent.token_tracker import make_token_tracker

# =============================================================================
# Classifies intent, extracts error context, and generates search queries
# =============================================================================
signal_extractor_agent = LlmAgent(
    name="signal_extractor_agent",
    model=MODEL_FAST,
    description="Classifies intent, extracts error context, generates search queries.",
    instruction=signal_extractor_instruction,
    output_schema=error_triage_result,
    output_key="error_triage_result",
    after_model_callback=make_token_tracker(MODEL_FAST_NAME),
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
)
