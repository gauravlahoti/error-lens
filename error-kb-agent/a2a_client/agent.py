import os

from google.adk.agents.llm_agent import Agent

from google.adk.agents.remote_a2a_agent import AGENT_CARD_WELL_KNOWN_PATH
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent

ERROR_KB_AGENT_URL = os.environ.get("ERROR_KB_AGENT_URL", "http://localhost:8080")
MODEL = os.environ.get("MODEL", "gemini-2.5-flash")

error_kb_agent = RemoteA2aAgent(
    name="error_kb_agent",
    description="Remote agent that searches, records, and manages GCP error resolutions from the error knowledge bank.",
    agent_card=(
        f"{ERROR_KB_AGENT_URL}{AGENT_CARD_WELL_KNOWN_PATH}"
    ),
    use_legacy=True,
)

root_agent = Agent(
    model=MODEL,
    name='root_agent',
    description='A GCP error resolution assistant backed by a knowledge bank of past incidents and fixes.',
    instruction='You are a senior GCP engineer colleagues come to when they hit errors. You have a knowledge bank of past incidents and resolutions at your disposal.',
    sub_agents=[error_kb_agent]
)


