"""
Bitwig MCP integration package.

This package provides MCP (Model Context Protocol) integration for Bitwig Studio.
"""

from .server import BitwigMCPServer
from .client import BitwigMCPClient
from .prompts import BitwigPrompts
from .resources import BitwigResources

__all__ = ["BitwigMCPServer", "BitwigMCPClient", "BitwigPrompts", "BitwigResources"]
