"""Knowledge bank A2A agents — search and record via the error-kb-agent."""

from google.adk.agents import LlmAgent
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent, AGENT_CARD_WELL_KNOWN_PATH

from error_lens_agent.config.config import MODEL_FAST, MODEL_BALANCED, KB_AGENT_URL
from error_lens_agent.models import kb_record_result
from error_lens_agent.prompts import kb_record_instruction, kb_resolve_instruction, kb_search_instruction

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
    description="Records the triaged error into the knowledge bank after synthesis.",
    instruction=kb_record_instruction,
    output_schema=kb_record_result,
    output_key="kb_record_result",
    sub_agents=[kb_record_remote],
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
)

# =============================================================================
# Knowledge bank search agent (A2A) — wrapped in LlmAgent for formatting
# =============================================================================
kb_search_remote = RemoteA2aAgent(
    name="kb_search_remote",
    description="Remote A2A connection to the error knowledge bank for searching resolved cases.",
    agent_card=f"{KB_AGENT_URL}{AGENT_CARD_WELL_KNOWN_PATH}",
    use_legacy=True,
)

kb_search_agent = LlmAgent(
    name="kb_search_agent",
    model=MODEL_BALANCED,
    description="Searches the knowledge bank for similar resolved cases and presents formatted results with next-step options.",
    instruction=kb_search_instruction,
    include_contents="none",
    sub_agents=[kb_search_remote],
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
)

# =============================================================================
# Knowledge bank resolve agent — deposits a confirmed fix for an existing case
# =============================================================================
kb_resolve_remote = RemoteA2aAgent(
    name="kb_resolve_remote",
    description="Remote agent for depositing confirmed fixes into the knowledge bank.",
    agent_card=f"{KB_AGENT_URL}{AGENT_CARD_WELL_KNOWN_PATH}",
    use_legacy=True,
)

kb_resolve_agent = LlmAgent(
    name="kb_resolve_agent",
    model=MODEL_BALANCED,
    description="Resolves an existing case by depositing the confirmed fix into the knowledge bank.",
    instruction=kb_resolve_instruction,
    sub_agents=[kb_resolve_remote],
)
