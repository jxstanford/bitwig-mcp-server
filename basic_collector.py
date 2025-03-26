#!/usr/bin/env python
"""
Basic device collector for Bitwig
"""

import asyncio
import json
import os
from pathlib import Path
from bitwig_mcp_server.osc.controller import BitwigOSCController


async def collect_devices():
    print("\nBasic Bitwig Device Collector")
    print("=" * 60)

    # Create data directory
    data_dir = Path(
        os.path.join(os.path.dirname(__file__), "data", "device_collection")
    )
    data_dir.mkdir(parents=True, exist_ok=True)

    # Create output file path
    devices_file = data_dir / "devices.json"

    # Create controller
    controller = BitwigOSCController()
    controller.start()

    try:
        # Wait for connection
        await asyncio.sleep(2.0)

        # Open the browser
        print("Opening browser...")
        controller.client.browse_for_device("after")
        await asyncio.sleep(2.0)

        # Check if browser opened
        browser_active = controller.server.get_message("/browser/isActive")
        print(f"Browser active: {browser_active}")

        if not browser_active:
            print("Browser did not open. Aborting.")
            return

        # Collect all devices visible in the current view
        print("\nCollecting visible devices...")
        devices = []

        # First, just collect what's visible without changing filters
        for i in range(1, 101):  # Check up to 100 devices
            result_exists = controller.server.get_message(f"/browser/result/{i}/exists")
            if not result_exists:
                print(f"No more devices after {i-1}")
                break

            device_name = controller.server.get_message(f"/browser/result/{i}/name")
            print(f"Found device: {device_name}")

            # Add to our list
            devices.append({"name": device_name, "index": i})

            await asyncio.sleep(0.1)  # Short pause

        print(f"\nCollected {len(devices)} devices.")

        # Close browser
        print("\nClosing browser...")
        controller.client.cancel_browser()
        await asyncio.sleep(1.0)

        # Save the data
        if devices:
            print(f"\nSaving {len(devices)} devices to {devices_file}")
            with open(devices_file, "w") as f:
                json.dump(devices, f, indent=2)
            print("Save complete!")
        else:
            print("No devices found to save.")

    finally:
        # Clean up
        controller.stop()
        print("Done.")


if __name__ == "__main__":
    asyncio.run(collect_devices())
