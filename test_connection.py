#!/usr/bin/env python
"""Test script to check connection with Bitwig Studio"""

import asyncio
from bitwig_mcp_server.osc.controller import BitwigOSCController


async def test_connection():
    print("Creating OSC controller...")
    controller = BitwigOSCController()

    print("Starting OSC controller...")
    controller.start()

    # Wait for connection
    print("Waiting for connection...")
    await asyncio.sleep(2.0)

    print("Sending play/stop commands to verify connection...")
    controller.client.play()  # Play
    await asyncio.sleep(1.0)
    controller.client.stop()  # Stop
    await asyncio.sleep(1.0)

    print("Refreshing OSC controller to request state updates...")
    controller.client.refresh()
    await asyncio.sleep(1.0)

    # Check for responses
    print("\nChecking for responses from Bitwig Studio:")
    print("-" * 60)

    # Try multiple state queries
    checks = [
        ("/play", "Transport Play State"),
        ("/tempo/raw", "Tempo"),
        ("/browser/isActive", "Browser Active"),
        ("/browser/exists", "Browser Exists"),
        ("/browser/tab", "Browser Tab"),
        ("/device/exists", "Device Exists"),
        ("/track/1/exists", "Track 1 Exists"),
    ]

    all_good = True

    for address, description in checks:
        value = controller.server.get_message(address)
        print(f"{description}: {value}")

        if value is None:
            all_good = False

    print("-" * 60)

    if all_good:
        print("\nSuccess! Connection to Bitwig Studio is working properly.")
    else:
        print("\nWarning: Some queries returned no response. Please check:")
        print("1. Bitwig Studio is running")
        print("2. A project is open in Bitwig")
        print("3. The Bitwig OSC Controller extension is loaded and enabled")
        print(
            "4. The OSC settings match: IP 127.0.0.1, sending on port 9000, receiving on port 8000"
        )

    print("\nTrying to open the browser...")
    controller.client.browse_for_device("after")
    await asyncio.sleep(2.0)

    # Check browser status
    browser_exists = controller.server.get_message("/browser/exists")
    print(f"Browser exists: {browser_exists}")

    browser_active = controller.server.get_message("/browser/isActive")
    print(f"Browser active: {browser_active}")

    browser_tab = controller.server.get_message("/browser/tab")
    print(f"Browser tab: {browser_tab}")

    # Test filter access
    for i in range(1, 7):  # Check 6 filters
        filter_exists = controller.server.get_message(f"/browser/filter/{i}/exists")
        if filter_exists:
            filter_name = controller.server.get_message(f"/browser/filter/{i}/name")
            print(f"Filter {i} exists: {filter_name}")

    # Close browser
    print("\nClosing browser...")
    controller.client.cancel_browser()
    await asyncio.sleep(1.0)

    # Stop the controller
    print("\nStopping OSC controller...")
    controller.stop()  # This is a synchronous method
    print("Test complete.")


if __name__ == "__main__":
    asyncio.run(test_connection())
