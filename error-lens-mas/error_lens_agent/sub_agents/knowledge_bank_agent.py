"""Knowledge bank agents — direct Toolbox search + A2A record/resolve."""

from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent, AGENT_CARD_WELL_KNOWN_PATH
from google.adk.tools.toolbox_toolset import ToolboxToolset

from error_lens_agent.config.config import MODEL_FAST, MODEL_FAST_NAME, MODEL_BALANCED, MODEL_BALANCED_NAME, KB_AGENT_URL, TOOLBOX_URL
from error_lens_agent.models import kb_record_input, kb_record_result
from error_lens_agent.prompts import kb_record_input_instruction, kb_record_instruction, kb_record_formatter_instruction, kb_search_instruction
from error_lens_agent.token_tracker import make_token_tracker

# =============================================================================
# Knowledge bank recorder — records new errors after synthesis (A2A)
# =============================================================================
kb_record_remote = RemoteA2aAgent(
    name="kb_record_remote",
    description="Remote agent for recording new errors into the knowledge bank.",
    agent_card=f"{KB_AGENT_URL}{AGENT_CARD_WELL_KNOWN_PATH}",
    use_legacy=True,
)

# Step 1: extract fields from state into a Pydantic-validated record — no tools, output_schema works on Gemini
kb_record_input_agent = LlmAgent(
    name="kb_record_input_agent",
    model=MODEL_BALANCED,
    description="Extracts error fields from session state into kb_record_input schema.",
    instruction=kb_record_input_instruction,
    include_contents="none",
    output_schema=kb_record_input,
    output_key="kb_record_input",
    after_model_callback=make_token_tracker(MODEL_BALANCED_NAME),
)

# Step 2: sends the structured input to kb_record_remote A2A — no output_schema so transfer_to_agent works
kb_record_caller_agent = LlmAgent(
    name="kb_record_caller_agent",
    model=MODEL_BALANCED,
    description=(
        "Transfers kb_record_input to kb_record_remote A2A agent. "
        "No output_schema — avoids ADK/Gemini conflict with transfer_to_agent."
    ),
    instruction=kb_record_instruction,
    include_contents="none",
    output_key="kb_record_raw_response",
    sub_agents=[kb_record_remote],
    after_model_callback=make_token_tracker(MODEL_BALANCED_NAME),
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
)

# Step 3: extracts case_ref from the A2A raw text response into structured output
kb_record_formatter_agent = LlmAgent(
    name="kb_record_formatter_agent",
    model=MODEL_FAST,
    description="Extracts case_ref from kb_record_raw_response into kb_record_result schema.",
    instruction=kb_record_formatter_instruction,
    include_contents="none",
    output_schema=kb_record_result,
    output_key="kb_record_result",
    after_model_callback=make_token_tracker(MODEL_FAST_NAME),
)

kb_record_pipeline = SequentialAgent(
    name="kb_record_pipeline",
    description="Records new case: extract fields → call A2A → structure case_ref.",
    sub_agents=[kb_record_input_agent, kb_record_caller_agent, kb_record_formatter_agent],
)

# =============================================================================
# Knowledge bank search — direct Toolbox call (bypasses A2A entirely)
# =============================================================================
kb_search_toolset = ToolboxToolset(
    server_url=TOOLBOX_URL,
    tool_names=["search-similar-errors"],
)

# =============================================================================
# KB stats — used by root_agent to show resolved/open counts on greeting
# =============================================================================
kb_stats_toolset = ToolboxToolset(
    server_url=TOOLBOX_URL,
    tool_names=["get-kb-stats"],
)

kb_search_agent = LlmAgent(
    name="kb_search_agent",
    model=MODEL_BALANCED,
    description="Searches the knowledge bank for similar resolved cases and presents formatted results with next-step options.",
    instruction=kb_search_instruction,
    include_contents="none",
    tools=[kb_search_toolset],
    after_model_callback=make_token_tracker(MODEL_BALANCED_NAME),
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
)

# =============================================================================
# Knowledge bank resolve agent — deposits a confirmed fix for an existing case
# =============================================================================
kb_resolve_remote = RemoteA2aAgent(
    name="kb_resolve_remote",
    description="Remote agent for resolving cases and listing open cases in the knowledge bank.",
    agent_card=f"{KB_AGENT_URL}{AGENT_CARD_WELL_KNOWN_PATH}",
    use_legacy=True,
)
