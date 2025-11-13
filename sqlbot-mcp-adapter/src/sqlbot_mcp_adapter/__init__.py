"""SQLBot MCP Adapter.

A Model Context Protocol (MCP) adapter for SQLBot integration.
"""

__version__ = "1.0.0"
__author__ = "SQLBot Team"

from .main import main
from .config import settings
from .mcp_server import MCPServer
from .sqlbot_client import SQLBotClient

__all__ = [
    "main",
    "settings",
    "MCPServer",
    "SQLBotClient"
]