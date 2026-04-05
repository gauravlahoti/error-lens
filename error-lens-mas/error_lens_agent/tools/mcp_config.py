"""Centralised MCP tool connections for ErrorLens.

All external tool integrations are declared here — credentials, endpoints,
and tool_filter configs in one place for easy auditing and rotation.
"""

from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams

from error_lens_agent.config.config import DEVELOPER_KNOWLEDGE_MCP_URL, DEVELOPER_KNOWLEDGE_API_KEY

# =============================================================================
# GCP Developer Knowledge MCP
# Provides semantic search over official GCP documentation.
# Docs: https://developers.google.com/products/developer-knowledge
# Env:  DEVELOPER_KNOWLEDGE_API_KEY
# =============================================================================
gcp_developer_knowledge_toolset = McpToolset(
    connection_params=StreamableHTTPConnectionParams(
        url=DEVELOPER_KNOWLEDGE_MCP_URL,
        headers={"X-Goog-Api-Key": DEVELOPER_KNOWLEDGE_API_KEY},
    ),
    tool_filter=["search_documents"],
)
