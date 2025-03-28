#!/usr/bin/env python
"""
Debug script to save device data without embeddings for debugging.

This script collects browser metadata from Bitwig but does not create embeddings,
saving only the raw device data for inspection. This is useful for debugging
browser collection issues without requiring ChromaDB or sentence transformers.
"""

import asyncio
import json
import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from bitwig_mcp_server.utils.browser_indexer import BitwigBrowserIndexer

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def save_devices_without_embeddings(output_dir: Optional[str] = None) -> bool:
    """
    Collect device data from Bitwig browser and save it without embeddings.

    Args:
        output_dir: Optional custom output directory path. If None, uses the default
                   data/browser_index directory.

    Returns:
        bool: True if collection was successful, False otherwise
    """
    logger.info("\nBitwig Device Collector - Metadata Only")
    logger.info("=" * 60)

    # Create data directory if it doesn't exist
    if output_dir:
        data_dir = Path(output_dir)
    else:
        data_dir = Path(
            os.path.join(os.path.dirname(__file__), "..", "data", "browser_index")
        )

    data_dir.mkdir(parents=True, exist_ok=True)

    # Create device data file path
    devices_file = data_dir / "devices_debug.json"

    # Create the indexer
    indexer = BitwigBrowserIndexer(persistent_dir=str(data_dir))

    try:
        # Initialize the controller
        logger.info("Initializing OSC controller...")
        controller_initialized = await indexer.initialize_controller()

        if not controller_initialized:
            logger.error("Failed to initialize controller. Is Bitwig running?")
            return False

        # Collect metadata
        logger.info("Collecting browser metadata...")
        browser_items = await indexer.collect_browser_metadata()

        if not browser_items:
            logger.error("No browser items collected.")
            return False

        logger.info(f"Collected {len(browser_items)} devices.")

        # Convert BrowserItem objects to dictionaries
        device_data: List[Dict[str, Any]] = []
        for item in browser_items:
            device_data.append(
                {"name": item.name, "metadata": item.metadata, "index": item.index}
            )

        # Save to JSON file
        logger.info(f"Saving device data to {devices_file}")
        with open(devices_file, "w") as f:
            json.dump(device_data, f, indent=2)

        logger.info(f"Successfully saved {len(device_data)} devices to {devices_file}")
        return True

    except Exception as e:
        logger.error(f"Error collecting browser data: {e}")
        return False
    finally:
        # Close the controller
        logger.info("Closing OSC controller...")
        await indexer.close_controller()
        logger.info("Done.")


async def analyze_device_categories(devices_file: Optional[str] = None) -> None:
    """
    Analyze device categories from saved device data.

    Args:
        devices_file: Path to the saved devices JSON file. If None, uses the default path.
    """
    # Determine file path
    if devices_file:
        file_path = Path(devices_file)
    else:
        file_path = Path(
            os.path.join(
                os.path.dirname(__file__),
                "..",
                "data",
                "browser_index",
                "devices_debug.json",
            )
        )

    if not file_path.exists():
        logger.error(
            f"Device file {file_path} not found. Run save_devices_without_embeddings first."
        )
        return

    # Load device data
    with open(file_path, "r") as f:
        device_data = json.load(f)

    logger.info(f"\nAnalyzing {len(device_data)} devices")

    # Analyze device categories
    categories: Dict[str, int] = {}
    device_types: Dict[str, int] = {}

    for device in device_data:
        metadata = device.get("metadata", {})

        # Extract category
        category = metadata.get("category", "Unknown")
        categories[category] = categories.get(category, 0) + 1

        # Extract device type
        device_type = metadata.get("device_type", "Unknown")
        device_types[device_type] = device_types.get(device_type, 0) + 1

    # Print statistics
    logger.info("\nDevice Categories:")
    for category, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
        logger.info(f"- {category}: {count} devices")

    logger.info("\nDevice Types:")
    for device_type, count in sorted(
        device_types.items(), key=lambda x: x[1], reverse=True
    ):
        logger.info(f"- {device_type}: {count} devices")


if __name__ == "__main__":
    # Run the device collection and analysis
    async def main():
        success = await save_devices_without_embeddings()
        if success:
            await analyze_device_categories()

    asyncio.run(main())
