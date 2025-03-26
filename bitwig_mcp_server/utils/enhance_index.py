#!/usr/bin/env python
"""
Index Enhancement Utility

This script enhances the Bitwig device index with additional information
from documentation sources.
"""

import argparse
import asyncio
import logging
import os
import sys
from typing import Dict

import requests
from bs4 import BeautifulSoup

from bitwig_mcp_server.utils.browser_indexer import BitwigBrowserIndexer


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)


class DeviceDescriptionScraper:
    """Scraper for Bitwig device descriptions from documentation."""

    def __init__(
        self,
        base_url: str = "https://www.bitwig.com/userguide/latest/device_descriptions/",
    ):
        """Initialize the scraper.

        Args:
            base_url: Base URL for the Bitwig device documentation
        """
        self.base_url = base_url

    def scrape_device_descriptions(self) -> Dict[str, str]:
        """Scrape device descriptions from the Bitwig documentation.

        Returns:
            Dictionary mapping device names to their descriptions
        """
        descriptions = {}

        try:
            # Get the main page
            response = requests.get(self.base_url)
            response.raise_for_status()

            # Parse the HTML
            soup = BeautifulSoup(response.text, "html.parser")

            # Look for device links
            device_links = soup.select("a[href^='./']")

            for link in device_links:
                device_name = link.text.strip()
                device_url = self.base_url + link["href"].replace("./", "")

                logger.info(f"Scraping description for: {device_name}")

                try:
                    # Get the device page
                    device_response = requests.get(device_url)
                    device_response.raise_for_status()

                    # Parse the device HTML
                    device_soup = BeautifulSoup(device_response.text, "html.parser")

                    # Extract the description
                    description_div = device_soup.select_one("div.description")
                    if description_div:
                        description = description_div.text.strip()
                        descriptions[device_name] = description
                        logger.info(
                            f"Found description for {device_name} ({len(description)} chars)"
                        )
                    else:
                        logger.warning(f"No description found for {device_name}")

                except Exception as e:
                    logger.warning(f"Error scraping device {device_name}: {e}")

        except Exception as e:
            logger.error(f"Error scraping device descriptions: {e}")

        return descriptions


async def enhance_index_with_descriptions(persistent_dir: str = None):
    """Enhance the device index with descriptions from documentation.

    Args:
        persistent_dir: Directory where the ChromaDB data is stored
    """
    # If no directory specified, use the project data directory
    if persistent_dir is None:
        persistent_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "data",
            "browser_index",
        )
    # Initialize the indexer with the existing data
    indexer = BitwigBrowserIndexer(persistent_dir=persistent_dir)

    # Check if the index exists
    if indexer.get_device_count() == 0:
        logger.error(
            f"No index found in {persistent_dir}. Please run index_browser.py --index first."
        )
        return

    # Get the existing device data
    collection = indexer.collection
    results = collection.get()

    # Get device descriptions
    scraper = DeviceDescriptionScraper()
    descriptions = scraper.scrape_device_descriptions()

    logger.info(f"Found {len(descriptions)} device descriptions from documentation")

    # Track how many descriptions were added
    updated_count = 0

    # Update the index with descriptions
    for i, doc_id in enumerate(results["ids"]):
        metadata = results["metadatas"][i]
        device_name = metadata["name"]

        # Check if we have a description for this device
        if device_name in descriptions and not metadata.get("description"):
            # Update the metadata with the description
            metadata["description"] = descriptions[device_name]

            # Update the document text to include the description
            document = results["documents"][i]
            if "Description:" not in document:
                document += f" Description: {descriptions[device_name]}."

            # Update the embedding with the new text
            embedding = indexer.create_embedding(document)

            # Update the collection
            collection.update(
                ids=[doc_id],
                embeddings=[embedding],
                metadatas=[metadata],
                documents=[document],
            )

            updated_count += 1
            logger.info(f"Updated {device_name} with description")

    logger.info(f"Enhanced {updated_count} devices with descriptions")


async def main():
    """Main function to handle command-line arguments."""
    parser = argparse.ArgumentParser(description="Bitwig Device Index Enhancement Tool")

    parser.add_argument(
        "--persistent-dir",
        default=None,
        help="Directory where the vector database is stored (default: project's data/browser_index)",
    )

    # Parse arguments
    args = parser.parse_args()

    # Enhance the index
    await enhance_index_with_descriptions(persistent_dir=args.persistent_dir)


if __name__ == "__main__":
    asyncio.run(main())
