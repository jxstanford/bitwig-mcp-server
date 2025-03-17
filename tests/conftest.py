"""
conftest.py - Configuration for pytest

This file contains fixtures that are available to all test files
"""

import os
import socket
import sys

import pytest

# Add the parent directory to sys.path to make the module importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def is_bitwig_running():
    """Check if Bitwig is likely running by trying to connect to its OSC port"""
    try:
        # Create socket and try to connect to Bitwig's default OSC port
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.1)
        s.connect(("127.0.0.1", 8000))
        s.close()
    except (OSError, socket.timeout):
        return False
    else:
        return True


# Skip marker for tests that require Bitwig to be running
skip_if_bitwig_not_running = pytest.mark.skipif(
    not is_bitwig_running(), reason="Bitwig Studio does not appear to be running"
)
