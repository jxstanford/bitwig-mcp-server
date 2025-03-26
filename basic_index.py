#!/usr/bin/env python
"""
Basic device index creator
"""

import asyncio
import json
import os
from pathlib import Path
from bitwig_mcp_server.osc.controller import BitwigOSCController


async def create_basic_index():
    print("\nBitwig Basic Device Index Creator")
    print("=" * 60)

    # Create data directory
    data_dir = Path(os.path.join(os.path.dirname(__file__), "data", "basic_index"))
    data_dir.mkdir(parents=True, exist_ok=True)

    # Output file
    devices_file = data_dir / "devices.json"

    # Create controller
    controller = BitwigOSCController()
    controller.start()

    try:
        # Wait for connection
        print("Establishing connection...")
        await asyncio.sleep(2.0)

        print("\nOpening browser...")
        controller.client.browse_for_device("after")
        await asyncio.sleep(2.0)

        # Check browser status
        browser_active = controller.server.get_message("/browser/isActive")
        print(f"Browser active: {browser_active}")

        if not browser_active:
            print("Browser did not open. Exiting.")
            return

        # Collect available devices
        print("\nCollecting device information...")
        devices = []

        for i in range(1, 101):  # Check up to 100 devices
            result_exists = controller.server.get_message(f"/browser/result/{i}/exists")
            if not result_exists:
                print(f"No more results after {i-1}")
                break

            device_name = controller.server.get_message(f"/browser/result/{i}/name")
            print(f"Found device: {device_name}")

            # Create a simple device record
            device = {
                "name": device_name,
                "index": i,
                "type": "Unknown",  # We could set this if we knew the device type
                "metadata": {},
            }

            devices.append(device)

        print(f"\nCollected information for {len(devices)} devices")

        # Close browser
        print("\nClosing browser...")
        controller.client.cancel_browser()
        await asyncio.sleep(1.0)

        # Save the data
        if devices:
            print(f"\nSaving device index to {devices_file}")
            with open(devices_file, "w") as f:
                json.dump(devices, f, indent=2)
            print("Device index saved successfully!")

            # Create a simple vector database placeholder
            db_file = data_dir / "vector_db.json"
            print(f"\nCreating placeholder vector database at {db_file}")

            # Create a simple vector database structure
            vector_db = {
                "name": "Bitwig Device Index",
                "description": "Simple device index for semantic search",
                "devices": [
                    {
                        "id": f"device_{i+1}",
                        "name": device["name"],
                        "metadata": device["metadata"],
                        # Use random vectors as placeholders since we can't generate embeddings
                        "embedding": [0.1, 0.2, 0.3, 0.4, 0.5],
                    }
                    for i, device in enumerate(devices)
                ],
            }

            with open(db_file, "w") as f:
                json.dump(vector_db, f, indent=2)

            print("Vector database placeholder created successfully!")
        else:
            print("No devices found to index.")

    finally:
        # Clean up
        controller.stop()
        print("Done.")


if __name__ == "__main__":
    asyncio.run(create_basic_index())
