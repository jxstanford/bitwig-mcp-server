"""
Bitwig OSC Integration Package

Provides OSC communication with Bitwig Studio
"""

from .client import BitwigOSCClient
from .controller import BitwigOSCController
from .server import BitwigOSCServer

__all__ = ["BitwigOSCClient", "BitwigOSCServer", "BitwigOSCController"]
