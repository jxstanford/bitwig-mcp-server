"""
Bitwig MCP Server

A Python library and server implementation for integrating
Bitwig Studio with the Model Context Protocol (MCP).
"""

from .app import main
from .mcp.server import BitwigMCPServer
from .settings import Settings, get_settings

__all__ = ["Settings", "BitwigMCPServer", "main", "get_settings"]
