#!/usr/bin/env python
"""
Absolutely minimal test for browser functions
"""

import time
from bitwig_mcp_server.osc.client import BitwigOSCClient

# Create the OSC client
client = BitwigOSCClient()

# Start with an empty OSC log
client.addr_log = []

print("\nTesting browser commands...")

# 1. Open browser
print("1. Opening browser...")
client.browse_for_device("after")
time.sleep(2)

# 2. Print the OSC messages sent so far
print("\nOSC messages sent:")
for addr in client.addr_log:
    print(f"- {addr}")

print("\nDone! Please check if the browser opened in Bitwig Studio.")
