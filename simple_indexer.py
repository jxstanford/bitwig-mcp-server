#!/usr/bin/env python
"""
Simplified device indexer for Bitwig Studio
"""

import asyncio
import json
import os
from pathlib import Path
from bitwig_mcp_server.osc.controller import BitwigOSCController


async def index_devices():
    print("\nSimplified Bitwig Device Indexer")
    print("=" * 60)

    # Create data directory
    data_dir = Path(os.path.join(os.path.dirname(__file__), "data", "simple_index"))
    data_dir.mkdir(parents=True, exist_ok=True)

    # Create output file path
    devices_file = data_dir / "devices.json"

    # Create controller
    controller = BitwigOSCController()
    controller.start()

    try:
        # Wait for connection
        print("Waiting for connection...")
        await asyncio.sleep(2)

        # Open browser
        print("Opening browser...")
        controller.client.browse_for_device("after")
        await asyncio.sleep(2)

        # Check if browser opened
        browser_active = controller.server.get_message("/browser/isActive")
        print(f"Browser active: {browser_active}")

        if not browser_active:
            print("Browser did not open. Aborting.")
            return

        # Define device types to explore
        device_types = ["Audio FX", "Instrument", "Note FX"]

        # Find the device type filter (usually filter 6)
        device_type_filter = None
        for filter_idx in range(1, 7):
            filter_name = controller.server.get_message(
                f"/browser/filter/{filter_idx}/name"
            )
            if filter_name == "Device Type":
                device_type_filter = filter_idx
                print(f"Found Device Type filter at index {filter_idx}")
                break

        if device_type_filter is None:
            print(
                "Could not find Device Type filter. Using default collection approach."
            )
            device_type_filter = 6  # Try the default location

        # Collect devices for each device type
        devices = []
        device_count = 0

        for device_type in device_types:
            print(f"\nCollecting {device_type} devices...")

            # First, reset all filters
            for filter_idx in range(1, 7):
                controller.client.reset_browser_filter(filter_idx)
            await asyncio.sleep(1.0)

            # Find and select the device type in the filter
            device_type_item_idx = None
            for item_idx in range(1, 17):
                item_exists = controller.server.get_message(
                    f"/browser/filter/{device_type_filter}/item/{item_idx}/exists"
                )
                if item_exists:
                    item_name = controller.server.get_message(
                        f"/browser/filter/{device_type_filter}/item/{item_idx}/name"
                    )
                    if item_name == device_type:
                        device_type_item_idx = item_idx
                        print(f"Found {device_type} at item index {item_idx}")
                        break

            if device_type_item_idx is None:
                print(
                    f"Could not find {device_type} in the Device Type filter. Skipping."
                )
                continue

            # Select the device type by navigating to it
            # First make sure we reset selection
            controller.client.reset_browser_filter(device_type_filter)
            await asyncio.sleep(0.5)

            # Navigate to the item
            for _ in range(device_type_item_idx):
                controller.client.navigate_browser_filter(device_type_filter, "+")
                await asyncio.sleep(0.2)

            # Check if selection worked
            selected = controller.server.get_message(
                f"/browser/filter/{device_type_filter}/item/{device_type_item_idx}/isSelected"
            )
            if not selected:
                print(f"Failed to select {device_type}. Skipping.")
                continue

            print(f"Successfully selected {device_type}.")
            await asyncio.sleep(1.0)  # Wait for browser to update

            # Now collect the devices for this type
            max_devices = 200  # Maximum number of devices to collect per type
            type_device_count = 0

            for i in range(1, max_devices + 1):
                result_exists = controller.server.get_message(
                    f"/browser/result/{i}/exists"
                )
                if not result_exists:
                    print(f"No more {device_type} devices after {type_device_count}")
                    break

                device_name = controller.server.get_message(f"/browser/result/{i}/name")
                print(f"Device {device_count + i}: {device_name} ({device_type})")

                # Create a device entry with type information
                device = {
                    "name": device_name,
                    "index": device_count + i,
                    "type": device_type,
                }

                devices.append(device)
                type_device_count += 1

                # Brief pause to avoid overloading Bitwig
                await asyncio.sleep(0.1)

            # Update overall device count
            device_count += type_device_count
            print(f"Collected {type_device_count} {device_type} devices")

            # Pause before switching device types
            await asyncio.sleep(1.0)

        # Close browser
        print("\nClosing browser...")
        controller.client.cancel_browser()
        await asyncio.sleep(1)

        # Save device information
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
    asyncio.run(index_devices())
