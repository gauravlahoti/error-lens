"""
Tool configuration for the Error KB Agent.

Connects to MCP Toolbox for Databases to access the error knowledge
bank via the ToolboxToolset.
"""

import os
from dotenv import load_dotenv
from google.adk.tools.toolbox_toolset import ToolboxToolset

load_dotenv()

TOOLBOX_URL = os.environ.get("TOOLBOX_URL")

if not TOOLBOX_URL:
    raise ValueError("TOOLBOX_URL environment variable is required")

# Connect to the MCP Toolbox for Databases server
# Uses the "error-kb-toolbox" toolset which provides error search and fix tools
error_kb_toolset = ToolboxToolset(
    server_url=TOOLBOX_URL,
    toolset_name="error-kb-toolbox",
)
