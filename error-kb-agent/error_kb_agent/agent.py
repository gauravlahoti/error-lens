import os
import pathlib
from dotenv import load_dotenv
from google.adk.agents.llm_agent import Agent
from error_kb_agent.tools import error_kb_toolset
from google.adk.a2a.utils.agent_to_a2a import to_a2a    
from google.adk.skills import load_skill_from_dir
from google.adk.tools import skill_toolset

load_dotenv()

MODEL = os.environ.get("MODEL", "gemini-2.5-flash")
SKILLS_DIR = pathlib.Path(__file__).parent / "skills"

# ── Skill gate callback ──────────────────────────────────────
# list_skills is auto-injected (L1) on every request.
# Domain tools are blocked until load_skill (L2) has been called.
# State is stored in tool_context.state (per-session) so the gate
# resets correctly on every new request instead of leaking across sessions.
_SKILL_TOOLS = {"list_skills", "load_skill", "load_skill_resource", "run_skill_script"}

# deposit-fix is blocked until get-case-by-id has been called first in this
# session — enforces the resolve-case workflow at code level so the LLM cannot
# skip showing suggested fixes to the engineer.
_REQUIRES_CASE_LOOKUP = {"deposit-fix"}
_CASE_LOOKUP_TOOL = "get-case-by-id"

def _require_skill_first(tool, args, tool_context):
    """Block domain-tool calls until a skill is loaded.

    Also enforces that deposit-fix cannot be called before get-case-by-id
    so the engineer always sees the stored suggested fixes first.
    """
    state = tool_context.state

    if tool.name in _SKILL_TOOLS:
        state["_skill_loaded"] = True
        return None

    if not state.get("_skill_loaded", False):
        return {
            "error": (
                f"Cannot call '{tool.name}' yet. "
                "First use `list_skills` and `load_skill` to discover the correct workflow."
            )
        }

    if tool.name == _CASE_LOOKUP_TOOL:
        state["_case_looked_up"] = True
        return None

    if tool.name in _REQUIRES_CASE_LOOKUP and not state.get("_case_looked_up", False):
        return {
            "error": (
                f"Cannot call '{tool.name}' before calling '{_CASE_LOOKUP_TOOL}'. "
                "You MUST call 'get-case-by-id' first and present the stored suggested "
                "fixes to the engineer before asking which one worked."
            )
        }

    return None

# ── Load skills ───────────────────────────────────────────────
search_errors_skill = load_skill_from_dir(SKILLS_DIR / "search-errors")
open_cases_skill = load_skill_from_dir(SKILLS_DIR / "open-cases")
resolve_case_skill = load_skill_from_dir(SKILLS_DIR / "resolve-case")
log_error_skill = load_skill_from_dir(SKILLS_DIR / "log-error")

kb_skill_toolset = skill_toolset.SkillToolset(
    skills=[search_errors_skill, open_cases_skill, resolve_case_skill, log_error_skill]
)


root_agent = Agent(
    model=MODEL,
    name='error_kb_agent',
    description=("A persistent knowledge bank agent for storing, searching, and managing "
        "GCP error resolutions backed by AlloyDB with vector embeddings."),
instruction=(
        "You are a knowledge bank agent that manages GCP error resolutions.\n\n"
        "MANDATORY: Your FIRST action on EVERY request — without exception — is to call\n"
        "`load_skill`. Do NOT emit any text, greeting, or explanation before calling\n"
        "`load_skill`. The skill listing injected into your context tells you which\n"
        "skill name to pass.\n\n"
        "After load_skill returns:\n"
        "1. Call `load_skill_resource` for any reference guides the skill requires.\n"
        "2. Execute the domain tools exactly as the skill workflow directs.\n"
        "3. Only then respond to the user with results in plain language.\n\n"
        "Never guess or invent tool names. Only call tools listed in the\n"
        "loaded skill's instructions.\n\n"
        "Never mention skill names, tool names, or internal implementation\n"
        "details in your responses.\n\n"
        "Only handle knowledge bank operations — "
        "for anything outside this scope, say so clearly and stop."
    ),
    tools=[kb_skill_toolset, error_kb_toolset],
    before_tool_callback=_require_skill_first,
)

# Make your agent A2A-compatible
# Set A2A_BASE_URL env var in Cloud Run to advertise the correct public URL in the agent card.
_base_url = os.environ.get("A2A_BASE_URL")
if _base_url:
    from urllib.parse import urlparse
    _p = urlparse(_base_url)
    a2a_app = to_a2a(root_agent, host=_p.hostname, port=_p.port or 443, protocol=_p.scheme)
else:
    a2a_app = to_a2a(root_agent, port=int(os.environ.get("PORT", "8001")))