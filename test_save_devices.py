#!/usr/bin/env python
"""
Test script to save device data without embeddings for debugging
"""

import asyncio
import json
import os
from pathlib import Path
from bitwig_mcp_server.utils.browser_indexer import BitwigBrowserIndexer


async def save_devices_without_embeddings():
    print("\nBitwig Device Indexer - Save Only Mode")
    print("=" * 60)

    # Create data directory if it doesn't exist
    data_dir = Path(os.path.join(os.path.dirname(__file__), "data", "browser_index"))
    data_dir.mkdir(parents=True, exist_ok=True)

    # Create device data file path
    devices_file = data_dir / "devices.json"

    # Create the indexer
    indexer = BitwigBrowserIndexer(persistent_dir=str(data_dir))

    try:
        # Initialize the controller
        print("Initializing OSC controller...")
        controller_initialized = await indexer.initialize_controller()

        if not controller_initialized:
            print("Failed to initialize controller. Is Bitwig running?")
            return

        # Collect metadata
        print("Collecting browser metadata...")
        browser_items = await indexer.collect_browser_metadata()

        if not browser_items:
            print("No browser items collected.")
            return

        print(f"Collected {len(browser_items)} devices.")

        # Convert BrowserItem objects to dictionaries
        device_data = []
        for item in browser_items:
            device_data.append(
                {"name": item.name, "metadata": item.metadata, "index": item.index}
            )

        # Save to JSON file
        print(f"Saving device data to {devices_file}")
        with open(devices_file, "w") as f:
            json.dump(device_data, f, indent=2)

        print(f"Successfully saved {len(device_data)} devices to {devices_file}")

    finally:
        # Close the controller
        print("Closing OSC controller...")
        await indexer.close_controller()
        print("Done.")


if __name__ == "__main__":
    asyncio.run(save_devices_without_embeddings())
