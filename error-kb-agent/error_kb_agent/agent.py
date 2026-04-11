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
_SKILL_TOOLS = {"list_skills", "load_skill", "load_skill_resource", "run_skill_script"}
_skill_loaded = False

def _require_skill_first(tool, args, tool_context):
    """Block domain-tool calls until a skill is loaded."""
    global _skill_loaded
    if tool.name in _SKILL_TOOLS:
        _skill_loaded = True
        return None
    if not _skill_loaded:
        return {
            "error": (
                f"Cannot call '{tool.name}' yet. "
                "First use `list_skills` and `load_skill` to discover the correct workflow."
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
        "Your available skills are automatically listed at the start of every\n"
        "request (L1 — auto-injected). You do NOT need to call `list_skills`\n"
        "yourself — the skill names and descriptions are already in context.\n\n"
        "To handle a request:\n"
        "1. Read the auto-injected skill listing to pick the right skill.\n"
        "2. Call `load_skill` with the skill name to get the workflow steps (L2).\n"
        "3. Follow the steps — call `load_skill_resource` for any reference\n"
        "   guides the skill requires (L3), then call the domain tools.\n\n"
        "Never guess or invent tool names. Only call tools listed in the\n"
        "loaded skill's instructions.\n\n"
        "When responding to users, speak naturally and describe what you can do "
        "in plain language. Never mention skill names, tool names, or any "
        "internal implementation details in your responses.\n\n"
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