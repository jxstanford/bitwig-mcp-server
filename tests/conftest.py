"""
conftest.py - Configuration for pytest

This file contains fixtures that are available to all test files
"""

import os
import sys

# Add the parent directory to sys.path to make the module importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# You can add global fixtures here if needed
