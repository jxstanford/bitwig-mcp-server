"""
Bitwig MCP Server

A Python library and server implementation for integrating
Bitwig Studio with the Model Context Protocol (MCP).
"""

from .server import BitwigMCPServer, main
from .settings import Settings

__all__ = ["Settings", "BitwigMCPServer", "main"]
