"""
Bitwig MCP integration package.

This package provides MCP (Model Context Protocol) integration for Bitwig Studio.
"""

from .resources import get_bitwig_resources, read_resource
from .tools import get_bitwig_tools, execute_tool

__all__ = ["get_bitwig_resources", "read_resource", "get_bitwig_tools", "execute_tool"]
