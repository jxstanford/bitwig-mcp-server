#!/usr/bin/env python
"""
Debug browser filter access in Bitwig
"""

import time
from bitwig_mcp_server.osc.client import BitwigOSCClient

# Create OSC client
client = BitwigOSCClient()

print("\nDebugging Bitwig Browser Filters")
print("=" * 60)

# Open browser
print("Opening browser...")
client.browse_for_device("after")
time.sleep(2)

# Check filters one by one
print("\nChecking filter indices...")
for i in range(1, 11):  # Check more indices than expected
    print(f"Sending message to /browser/filter/{i}/exists")
    client.send(f"/browser/filter/{i}/exists", None)
    time.sleep(0.2)

# Try checking first filter directly
print("\nChecking first filter name...")
client.send("/browser/filter/1/name", None)

print("\nDone!")
print("Check if you see any response from Bitwig after each message.")
