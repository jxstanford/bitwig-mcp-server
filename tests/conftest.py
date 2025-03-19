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
    # First check environment variable
    if os.environ.get("BITWIG_TESTS_ENABLED", "").lower() in ("1", "true", "yes"):
        print("Bitwig integration tests enabled via environment variable")
        return True

    if os.environ.get("BITWIG_TESTS_DISABLED", "").lower() in ("1", "true", "yes"):
        print("Bitwig integration tests disabled via environment variable")
        return False

    # Otherwise check for Bitwig
    import subprocess

    # Check if Bitwig is running using ps command
    try:
        result = subprocess.run(["ps", "-A"], capture_output=True, text=True)
        if "Bitwig Studio" in result.stdout:
            print("Bitwig Studio is running!")
            return True
    except Exception:
        pass

    # If process check fails, try the network approach
    try:
        # Create socket and try to connect to Bitwig's default OSC port
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)  # Longer timeout to allow for response
        s.sendto(b"/project/name\0\0\0\0,\0\0\0", ("127.0.0.1", 8000))

        # Try to receive a response
        try:
            s.recvfrom(1024)
            print("Received OSC response from port 8000")
            s.close()
            return True
        except (socket.timeout, OSError):
            pass
        finally:
            s.close()
    except Exception as e:
        print(f"Error checking Bitwig: {e}")

    return False


# Skip marker for tests that require Bitwig to be running
skip_if_bitwig_not_running = pytest.mark.skipif(
    not is_bitwig_running(), reason="Bitwig Studio does not appear to be running"
)
