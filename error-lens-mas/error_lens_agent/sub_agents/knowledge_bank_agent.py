"""Knowledge bank agents — direct Toolbox search + A2A record/resolve."""

from google.adk.agents import LlmAgent
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent, AGENT_CARD_WELL_KNOWN_PATH
from google.adk.tools.toolbox_toolset import ToolboxToolset

from error_lens_agent.config.config import MODEL_FAST, MODEL_BALANCED, MODEL_BALANCED_NAME, KB_AGENT_URL, TOOLBOX_URL
from error_lens_agent.models import kb_record_result
from error_lens_agent.prompts import kb_record_instruction, kb_search_instruction
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

kb_record_agent = LlmAgent(
    name="kb_record_agent",
    model=MODEL_BALANCED,
    description="Records the triaged error into the knowledge bank.",
    instruction=kb_record_instruction,
    output_schema=kb_record_result,
    output_key="kb_record_result",
    sub_agents=[kb_record_remote],
    after_model_callback=make_token_tracker(MODEL_BALANCED_NAME),
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
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
