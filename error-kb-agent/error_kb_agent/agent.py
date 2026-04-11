import os
import re
import pathlib
from dotenv import load_dotenv
from google.adk.agents.llm_agent import Agent
from error_kb_agent.tools import error_kb_toolset
# from error_kb_agent.prompts import AGENT_INSTRUCTION
from google.adk.a2a.utils.agent_to_a2a import to_a2a    
from google.adk.skills import load_skill_from_dir
from google.adk.tools import skill_toolset

load_dotenv()

MODEL = os.environ.get("MODEL", "gemini-2.5-flash")
SKILLS_DIR = pathlib.Path(__file__).parent / "skills"

# ── Skill gate callback ──────────────────────────────────────
# 1. Domain tools blocked until a skill is loaded.
# 2. Once a domain tool runs, load_skill is blocked (one skill per request).
# Module-level flags persist across A2A sessions within the same process.
_SKILL_TOOLS = {"list_skills", "load_skill", "load_skill_resource", "run_skill_script"}
_skill_loaded = False
_domain_tool_executed = False

def _require_skill_first(tool, args, tool_context):
    """Block domain-tool calls until a skill is loaded; one skill per request."""
    global _skill_loaded, _domain_tool_executed
    if tool.name == "list_skills":
        _skill_loaded = True
        _domain_tool_executed = False          # reset for new request
        return None
    if tool.name == "load_skill" and _domain_tool_executed:
        return {"error": "One skill per request. Respond with the result you have."}
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
    _domain_tool_executed = True               # mark: skill work done
    return None

# ── Redaction callback ────────────────────────────────────────
# Strip internal skill/tool names from text responses before they reach users.
_INTERNAL_NAMES = [
    "search-errors", "open-cases", "resolve-case", "log-error",
    "list_skills", "load_skill", "load_skill_resource", "run_skill_script",
    "search-similar-errors", "get-case-by-id", "get-open-cases",
    "deposit-fix", "record-new-error",
    "error_kb_toolset", "kb_skill_toolset", "SkillToolset", "ToolboxToolset",
    "before_tool_callback", "after_model_callback",
]
_REDACT_RE = re.compile(
    r"`?(?:" + "|".join(re.escape(n) for n in sorted(_INTERNAL_NAMES, key=len, reverse=True)) + r")`?",
    re.IGNORECASE,
)

def _redact_internals(callback_context, llm_response):
    """Remove leaked skill/tool names from text parts of the LLM response."""
    if not llm_response or not llm_response.content or not llm_response.content.parts:
        return None
    changed = False
    for part in llm_response.content.parts:
        if part.text:
            cleaned = _REDACT_RE.sub("", part.text)
            cleaned = re.sub(r",\s*,", ",", cleaned)
            cleaned = re.sub(r":\s*,", ":", cleaned)
            cleaned = re.sub(r"\s{2,}", " ", cleaned)
            cleaned = cleaned.strip()
            if cleaned != part.text:
                part.text = cleaned
                changed = True
    return llm_response if changed else None

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
        "You do NOT know your tool names in advance. You MUST discover them:\n"
        "1. Call `list_skills` to see available skills.\n"
        "2. Call `load_skill` with the skill name to learn the exact tools and workflow.\n"
        "3. Only then call the tools the skill told you to use.\n\n"
        "Never guess or invent tool names. Your only starting tools are "
        "`list_skills` and `load_skill`.\n\n"
        "When responding to users, speak naturally and describe what you can do "
        "in plain language. Never mention skill names, tool names, or any "
        "internal implementation details in your responses.\n\n"
        "Only handle knowledge bank operations — "
        "for anything outside this scope, say so clearly and stop."
    ),
    tools=[kb_skill_toolset, error_kb_toolset],
    before_tool_callback=_require_skill_first,
    after_model_callback=_redact_internals,
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