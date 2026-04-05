import os
from dotenv import load_dotenv
from google.adk.agents.llm_agent import Agent
from error_kb_agent.tools import error_kb_toolset
from error_kb_agent.prompts import AGENT_INSTRUCTION
from google.adk.a2a.utils.agent_to_a2a import to_a2a    

load_dotenv()

MODEL = os.environ.get("MODEL", "gemini-2.5-flash")

root_agent = Agent(
    model=MODEL,
    name='error_kb_agent',
    description='Searches, records, and manages GCP error resolutions from the error knowledge bank.',
    instruction=AGENT_INSTRUCTION,
    tools=[error_kb_toolset],
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