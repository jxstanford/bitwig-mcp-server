#!/usr/bin/env python
"""
Audio FX collector for Bitwig
"""

import asyncio
import json
import os
from pathlib import Path
from bitwig_mcp_server.osc.controller import BitwigOSCController


async def collect_audio_fx():
    print("\nBitwig Audio FX Collector")
    print("=" * 60)

    # Create data directory
    data_dir = Path(
        os.path.join(os.path.dirname(__file__), "data", "audio_fx_collection")
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

        # Try to select Audio FX in the Device Type filter (assumed to be filter 6)
        device_type_filter = 6  # Common location for Device Type filter

        print(f"\nChecking Device Type filter ({device_type_filter})...")
        filter_name = controller.server.get_message(
            f"/browser/filter/{device_type_filter}/name"
        )
        print(f"Filter {device_type_filter} name: {filter_name}")

        # If it's the Device Type filter, select Audio FX
        if filter_name == "Device Type":
            print("Found Device Type filter. Looking for Audio FX option...")

            # Reset the filter first
            controller.client.reset_browser_filter(device_type_filter)
            await asyncio.sleep(0.5)

            # Look for Audio FX
            audio_fx_found = False
            for item_idx in range(1, 17):
                item_exists = controller.server.get_message(
                    f"/browser/filter/{device_type_filter}/item/{item_idx}/exists"
                )
                if item_exists:
                    item_name = controller.server.get_message(
                        f"/browser/filter/{device_type_filter}/item/{item_idx}/name"
                    )
                    print(f"  Item {item_idx}: {item_name}")

                    if item_name == "Audio FX":
                        print(f"Found Audio FX at item {item_idx}. Selecting...")
                        audio_fx_found = True

                        # Navigate to Audio FX
                        for _ in range(item_idx):
                            controller.client.navigate_browser_filter(
                                device_type_filter, "+"
                            )
                            await asyncio.sleep(0.2)

                        is_selected = controller.server.get_message(
                            f"/browser/filter/{device_type_filter}/item/{item_idx}/isSelected"
                        )
                        print(f"Audio FX selected: {is_selected}")
                        break

            if not audio_fx_found:
                print(
                    "Could not find Audio FX option. Continuing with default filters."
                )
        else:
            print(
                f"Filter {device_type_filter} is not Device Type. Continuing with default filters."
            )

        # Wait for browser to update
        print("Waiting for browser to update...")
        await asyncio.sleep(2.0)

        # Now collect devices
        print("\nCollecting devices...")
        devices = []

        for i in range(1, 201):  # Check up to 200 devices
            result_exists = controller.server.get_message(f"/browser/result/{i}/exists")
            if not result_exists:
                print(f"No more devices after {i-1}")
                break

            device_name = controller.server.get_message(f"/browser/result/{i}/name")
            print(f"Found device: {device_name}")

            # Add to our list
            devices.append(
                {
                    "name": device_name,
                    "index": i,
                    "type": "Audio FX",  # Since we're specifically looking at Audio FX
                }
            )

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
    asyncio.run(collect_audio_fx())
