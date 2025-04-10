"""
Browser Indexer Utility

This module provides functionality to index the Bitwig Studio browser content
and store it in a ChromaDB vector database for semantic search.
"""

import asyncio
import json
import logging
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, TypedDict
from urllib.parse import urljoin

import chromadb
import requests
from bs4 import BeautifulSoup
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

from bitwig_mcp_server.osc.controller import BitwigOSCController

# Setup logging
logger = logging.getLogger(__name__)


# Define data structures for the device index
class DeviceMetadata(TypedDict):
    name: str
    type: str  # Instrument, Effect, etc.
    category: str  # EQ, Delay, Synth, etc.
    creator: str  # Bitwig, 3rd party, etc.
    tags: str  # Comma-separated string of tags (changed from List[str] for ChromaDB compatibility)
    description: Optional[str]  # May be provided later from documentation


@dataclass
class BrowserItem:
    name: str
    metadata: DeviceMetadata
    index: int  # Position in the browser


class BitwigBrowserIndexer:
    """Utility for indexing Bitwig browser content into a vector database."""

    def __init__(
        self,
        persistent_dir: str = None,
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        collection_name: str = "bitwig_devices",
    ):
        """Initialize the browser indexer.

        Args:
            persistent_dir: Directory to store the ChromaDB persistent data
            embedding_model: Name of the sentence transformer model to use
            collection_name: Name of the ChromaDB collection to store the device data
        """
        if persistent_dir is None:
            # Use the data directory in the project by default
            persistent_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "data",
                "browser_index",
            )

        self.persistent_dir = Path(persistent_dir)
        self.embedding_model_name = embedding_model
        self.collection_name = collection_name

        # Create the persistent directory if it doesn't exist
        self.persistent_dir.mkdir(parents=True, exist_ok=True)

        # Initialize the ChromaDB client
        self.chroma_client = chromadb.PersistentClient(
            path=str(self.persistent_dir), settings=Settings(anonymized_telemetry=False)
        )

        # Get or create the collection
        self.collection = self.get_or_create_collection()

        # Initialize the embedding model (lazy-loaded on first use)
        self._embedding_model = None

        # Initialize controller and client (will be set later)
        self.controller = None
        self.client = None

    @property
    def embedding_model(self) -> SentenceTransformer:
        """Lazy load the embedding model."""
        if self._embedding_model is None:
            logger.info(f"Loading embedding model: {self.embedding_model_name}")
            self._embedding_model = SentenceTransformer(self.embedding_model_name)
        return self._embedding_model

    def get_or_create_collection(self):
        """Get or create the ChromaDB collection."""
        try:
            # Try to get an existing collection
            collection = self.chroma_client.get_collection(
                name=self.collection_name,
                embedding_function=None,  # We'll handle embeddings ourselves
            )
            logger.info(f"Using existing collection: {self.collection_name}")
            return collection
        except Exception:
            # Collection doesn't exist, create a new one
            logger.info(
                f"Collection {self.collection_name} does not exist. Creating new collection."
            )
            return self.chroma_client.create_collection(
                name=self.collection_name,
                embedding_function=None,  # We'll handle embeddings ourselves
                metadata={"description": "Bitwig Studio browser device index"},
            )

    async def initialize_controller(self) -> bool:
        """Initialize the OSC controller for communicating with Bitwig.

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if self.controller is None:
                logger.info("Creating OSC controller...")
                try:
                    self.controller = BitwigOSCController()
                except Exception as e:
                    logger.error(f"Failed to create OSC controller: {e}")
                    logger.error(
                        "This may indicate a port conflict. Check if another application is using ports 8000 or 9000."
                    )
                    return False

                # Check if controller was created successfully
                if not self.controller:
                    logger.error("Failed to create OSC controller - returned None")
                    return False

                self.client = self.controller.client
                if not self.client:
                    logger.error("Failed to get OSC client from controller")
                    return False

                # Start the controller
                logger.info("Starting OSC controller...")
                try:
                    self.controller.start()
                except Exception as e:
                    logger.error(f"Failed to start OSC controller: {e}")
                    logger.error(
                        "This likely indicates a port conflict. Check if another application is using ports 8000 or 9000."
                    )
                    return False

                # Connect to Bitwig with retry logic
                max_retries = 3
                success = False

                for retry in range(max_retries):
                    logger.info(
                        f"Attempting to connect to Bitwig Studio (attempt {retry+1}/{max_retries})..."
                    )

                    # Refresh the controller to get initial state
                    self.client.refresh()
                    await asyncio.sleep(2.0)

                    # Try to get basic transport info
                    self.client.refresh()
                    await asyncio.sleep(1.0)

                    # Try multiple endpoints to verify connection
                    endpoints_to_check = [
                        "/transport/tempo",
                        "/browser/exists",
                        "/application/projectName",
                    ]

                    responses = []
                    for endpoint in endpoints_to_check:
                        response = self.controller.server.get_message(endpoint)
                        responses.append((endpoint, response))
                        if response is not None:
                            success = True

                    if success:
                        # Log which endpoints responded
                        for endpoint, response in responses:
                            if response is not None:
                                logger.info(
                                    f"✅ Received response from {endpoint}: {response}"
                                )
                        break

                    if retry < max_retries - 1:  # Don't wait after the last attempt
                        logger.warning(
                            f"No response from Bitwig Studio on attempt {retry+1}, retrying in 3 seconds..."
                        )
                        await asyncio.sleep(3.0)

                if not success:
                    logger.error(
                        "Failed to connect to Bitwig Studio after multiple attempts. Please check if:"
                        "\n1. Bitwig Studio is running with a project open"
                        "\n2. The OSC Controller extension is enabled in Bitwig settings"
                        "\n3. The correct ports are configured (8000 for sending to Bitwig, 9000 for receiving)"
                    )
                    return False

                logger.info("✅ Successfully connected to Bitwig Studio")
                return True
            return True
        except Exception as e:
            logger.exception(f"Error initializing controller: {e}")
            return False

    async def close_controller(self, external_controller=False) -> None:
        """Close the OSC controller.

        Args:
            external_controller: If True, don't actually close the controller as it's managed externally
        """
        try:
            if self.controller is not None and not external_controller:
                logger.info("Closing OSC controller...")
                self.controller.stop()  # This is a synchronous method
        except Exception as e:
            logger.warning(f"Error closing controller: {e}")
        finally:
            if not external_controller:
                self.controller = None
                self.client = None

    def create_embedding(self, text: str) -> List[float]:
        """Create embeddings for text using the sentence transformer model.

        Args:
            text: Text to embed

        Returns:
            List of embedding values
        """
        return self.embedding_model.encode(text).tolist()

    def create_search_text(self, device: BrowserItem) -> str:
        """Create a searchable text representation of a device.

        This combines name, category, creator, and tags into a single text string
        that can be used for embedding and semantic search.

        Args:
            device: The device item to create search text for

        Returns:
            A string representation for semantic search
        """
        metadata = device.metadata
        tags_text = metadata.get(
            "tags", ""
        )  # Tags are already a comma-separated string
        description = metadata.get("description", "")

        # Create a text representation that focuses on what the device does
        search_text = (
            f"Name: {metadata['name']}. "
            f"Type: {metadata.get('type', '')}. "
            f"Category: {metadata.get('category', '')}. "
            f"Creator: {metadata.get('creator', '')}. "
        )

        if tags_text:
            search_text += f"Tags: {tags_text}. "

        if description:
            search_text += f"Description: {description}. "

        return search_text

    async def navigate_browser_tabs(self) -> List[str]:
        """Navigate through all available tabs in the Bitwig browser,
        capturing tab names for later indexing.

        Returns:
            List of tab names found in the browser
        """
        if self.client is None:
            logger.error("Client not initialized")
            return []

        # First, try to open the browser with retry logic
        for attempt in range(3):  # Try up to 3 times
            logger.info(f"Opening Bitwig browser for device (attempt {attempt+1}/3)...")

            # Make sure client is refreshed
            self.client.refresh()
            await asyncio.sleep(1.0)

            # Try to open browser
            self.client.browse_for_device("after")
            await asyncio.sleep(2.0)  # Longer wait time for browser to open

            # Check if browser is active
            browser_active = self.controller.server.get_message("/browser/isActive")
            logger.info(f"Browser active: {browser_active}")

            if browser_active:
                break

            if attempt < 2:  # Don't log error on last attempt
                logger.warning(
                    f"Browser failed to open on attempt {attempt+1}, retrying..."
                )
                # Try closing browser if it might be stuck
                self.client.cancel_browser()
                await asyncio.sleep(1.0)

        # Final check if browser is active
        if not self.controller.server.get_message("/browser/isActive"):
            logger.error(
                "Browser failed to open after multiple attempts. Please check if:"
                "\n1. Bitwig Studio is running with a project open"
                "\n2. The OSC Controller extension is enabled in Bitwig"
                "\n3. Bitwig is not in fullscreen mode (try switching to window mode)"
            )
            return []

        # Clear the browser state by closing and reopening
        logger.info("Resetting browser state...")
        self.client.cancel_browser()
        await asyncio.sleep(1.0)
        self.client.browse_for_device("after")
        await asyncio.sleep(2.0)

        # Go to the first tab by repeatedly going back
        # This ensures we start from a consistent position
        logger.info("Navigating to first browser tab...")
        for _ in range(10):  # Try up to 10 times
            self.client.navigate_browser_tab("-")
            await asyncio.sleep(0.3)

        # Now collect all tabs by navigating forward
        tab_names = []
        max_tabs = 15  # Maximum number of tabs to check
        last_tab = None
        consecutive_fails = 0
        max_consecutive_fails = 3

        logger.info("Mapping all browser tabs...")

        for tab_index in range(max_tabs):
            # Get current tab name with retry
            current_tab = None
            for retry in range(3):
                current_tab = self.controller.server.get_message("/browser/tab")
                if current_tab is not None:
                    break
                await asyncio.sleep(0.5)
                self.client.refresh()
                await asyncio.sleep(0.5)

            # Skip if we couldn't get the tab name
            if current_tab is None:
                logger.warning(
                    f"Could not get name for tab {tab_index+1} after retries"
                )
                consecutive_fails += 1

                # If we have too many consecutive failures, try an alternative approach
                if consecutive_fails >= max_consecutive_fails:
                    logger.warning(
                        "Multiple tab detection failures, trying alternative approach..."
                    )
                    break

                # Try to move to next tab anyway
                self.client.navigate_browser_tab("+")
                await asyncio.sleep(0.7)  # Longer wait time after failure
                continue

            # Reset consecutive failures counter on success
            consecutive_fails = 0

            logger.info(f"Found tab {tab_index+1}: {current_tab}")

            # If we've seen this tab before, we've looped around
            if current_tab in tab_names:
                logger.info(f"Tab '{current_tab}' already found, finished mapping tabs")
                break

            # If this is the same as the last tab, we're not moving anymore
            if current_tab == last_tab and tab_index > 0:
                logger.info(f"Tab not changing, finished at '{current_tab}'")
                break

            # Add this tab to our list
            tab_names.append(current_tab)
            last_tab = current_tab

            # Move to the next tab
            self.client.navigate_browser_tab("+")
            await asyncio.sleep(0.7)  # Longer wait time for tab change

        # If we couldn't detect any tabs, use default tabs as fallback
        if not tab_names:
            logger.warning(
                "Could not detect browser tabs automatically. Using default tab names as fallback."
            )
            # These are the standard tabs in Bitwig Studio 5
            default_tabs = [
                "Result",
                "Instruments",
                "Audio FX",
                "Note FX",
                "Containers",
            ]
            logger.info(f"Using default tabs: {', '.join(default_tabs)}")
            return default_tabs

        logger.info(f"Found {len(tab_names)} browser tabs: {', '.join(tab_names)}")
        return tab_names

    async def navigate_to_tab(self, target_tab: str) -> bool:
        """Navigate to a specific browser tab.

        Args:
            target_tab: Name of the tab to navigate to

        Returns:
            True if successfully navigated, False otherwise
        """
        if self.client is None:
            logger.error("Client not initialized")
            return False

        # Check if browser is active
        browser_active = self.controller.server.get_message("/browser/isActive")
        if not browser_active:
            logger.error("Browser is not active")
            return False

        # Check current tab
        current_tab = self.controller.server.get_message("/browser/tab")
        logger.info(f"Current browser tab: {current_tab}")

        # Already on the target tab
        if current_tab == target_tab:
            logger.info(f"Already on the '{target_tab}' tab")
            return True

        # Navigate to the target tab
        max_attempts = 15
        logger.info(f"Looking for '{target_tab}' tab...")

        for attempt in range(max_attempts):
            # Navigate to the next tab
            self.client.navigate_browser_tab("+")
            await asyncio.sleep(0.5)

            current_tab = self.controller.server.get_message("/browser/tab")
            logger.info(
                f"Current browser tab ({attempt+1}/{max_attempts}): {current_tab}"
            )

            if current_tab == target_tab:
                logger.info(f"Successfully navigated to '{target_tab}' tab")
                return True

        logger.warning(
            f"Could not find '{target_tab}' tab after {max_attempts} attempts"
        )
        return False

    async def navigate_to_everything_tab(self) -> bool:
        """Navigate to the 'Result' tab in the browser.

        Returns:
            True if successfully navigated, False otherwise
        """
        # First, open the browser if not already open
        browser_active = self.controller.server.get_message("/browser/isActive")
        if not browser_active:
            logger.info("Opening Bitwig browser for device...")
            self.client.browse_for_device("after")
            await asyncio.sleep(1.0)

            # Check again
            browser_active = self.controller.server.get_message("/browser/isActive")
            if not browser_active:
                logger.error(
                    "Browser failed to open. Please ensure Bitwig Studio is running."
                )
                return False

        # Check current tab
        current_tab = self.controller.server.get_message("/browser/tab")
        logger.info(f"Current browser tab: {current_tab}")

        # In Bitwig Studio 5, the main browser tab appears to be called "Result" instead of "Everything"
        if current_tab == "Result" or current_tab == "Everything":
            logger.info(f"Successfully using the '{current_tab}' tab")
            return True

        # Try to find and navigate to the "Result" or "Everything" tab
        return await self.navigate_to_tab("Result") or await self.navigate_to_tab(
            "Everything"
        )

    async def check_total_browser_items(self) -> int:
        """Check how many total items are in the browser by examining the wildcards.

        Returns:
            The estimated total number of items in the browser
        """
        # First, ensure we're in the Everything/Result tab
        if not await self.navigate_to_everything_tab():
            logger.error("Failed to navigate to browser tab")
            return 0

        # Refresh to get current state
        self.client.refresh()
        await asyncio.sleep(1.0)

        # Get wildcard information from first filter (Location)
        location_wildcard_hits = None
        location_filter_name = self.controller.server.get_message(
            "/browser/filter/1/name"
        )
        location_wildcard = self.controller.server.get_message(
            "/browser/filter/1/wildcard"
        )

        if location_filter_name and location_wildcard:
            logger.info(
                f"Filter 1: {location_filter_name}, Wildcard: {location_wildcard}"
            )

            # Check all items in this filter to find the wildcard
            for i in range(1, 17):
                item_name = self.controller.server.get_message(
                    f"/browser/filter/1/item/{i}/name"
                )
                if item_name == location_wildcard:
                    hits = self.controller.server.get_message(
                        f"/browser/filter/1/item/{i}/hits"
                    )
                    logger.info(
                        f"Location filter wildcard '{location_wildcard}' has {hits} hits"
                    )
                    location_wildcard_hits = hits
                    break

        # Get wildcard information from second filter (File Type)
        filetype_wildcard_hits = None
        filetype_filter_name = self.controller.server.get_message(
            "/browser/filter/2/name"
        )
        filetype_wildcard = self.controller.server.get_message(
            "/browser/filter/2/wildcard"
        )

        if filetype_filter_name and filetype_wildcard:
            logger.info(
                f"Filter 2: {filetype_filter_name}, Wildcard: {filetype_wildcard}"
            )

            # Check all items in this filter to find the wildcard
            for i in range(1, 17):
                item_name = self.controller.server.get_message(
                    f"/browser/filter/2/item/{i}/name"
                )
                if item_name == filetype_wildcard:
                    hits = self.controller.server.get_message(
                        f"/browser/filter/2/item/{i}/hits"
                    )
                    logger.info(
                        f"File Type filter wildcard '{filetype_wildcard}' has {hits} hits"
                    )
                    filetype_wildcard_hits = hits
                    break

        # Also check Category filter if it exists
        category_wildcard_hits = None
        for filter_index in range(3, 7):
            filter_name = self.controller.server.get_message(
                f"/browser/filter/{filter_index}/name"
            )
            if filter_name and filter_name.lower() in ["category", "device type"]:
                category_wildcard = self.controller.server.get_message(
                    f"/browser/filter/{filter_index}/wildcard"
                )
                if category_wildcard:
                    logger.info(
                        f"Filter {filter_index}: {filter_name}, Wildcard: {category_wildcard}"
                    )

                    # Check all items in this filter to find the wildcard
                    for i in range(1, 17):
                        item_name = self.controller.server.get_message(
                            f"/browser/filter/{filter_index}/item/{i}/name"
                        )
                        if item_name == category_wildcard:
                            hits = self.controller.server.get_message(
                                f"/browser/filter/{filter_index}/item/{i}/hits"
                            )
                            logger.info(
                                f"Category filter wildcard '{category_wildcard}' has {hits} hits"
                            )
                            category_wildcard_hits = hits
                            break
                    break

        # Determine the most accurate count
        all_counts = [
            location_wildcard_hits,
            filetype_wildcard_hits,
            category_wildcard_hits,
        ]
        all_counts = [count for count in all_counts if count is not None]

        if all_counts:
            # Use the maximum count as it's the most inclusive
            total_items = max(all_counts)
            logger.info(f"Estimated total browser items: {total_items}")
            return total_items
        else:
            logger.warning("Could not determine total browser items")
            return 0

    async def check_item_counts_by_category(self) -> dict:
        """Check how many items are in each category by examining category filter items.

        Returns:
            Dictionary mapping category names to item counts
        """
        # First, ensure we're in the Everything/Result tab
        if not await self.navigate_to_everything_tab():
            logger.error("Failed to navigate to browser tab")
            return {}

        # Refresh to get current state
        self.client.refresh()
        await asyncio.sleep(1.0)

        # Find the category filter
        category_filter_index = None
        for filter_index in range(1, 7):
            filter_name = self.controller.server.get_message(
                f"/browser/filter/{filter_index}/name"
            )
            if filter_name and filter_name.lower() in ["category", "device type"]:
                category_filter_index = filter_index
                logger.info(
                    f"Found category filter at position {filter_index}: {filter_name}"
                )
                break

        if not category_filter_index:
            logger.warning("Could not find category filter")
            return {}

        # Get counts for each category
        category_counts = {}
        for item_index in range(1, 17):
            item_exists = self.controller.server.get_message(
                f"/browser/filter/{category_filter_index}/item/{item_index}/exists"
            )
            if not item_exists:
                continue

            item_name = self.controller.server.get_message(
                f"/browser/filter/{category_filter_index}/item/{item_index}/name"
            )
            item_hits = self.controller.server.get_message(
                f"/browser/filter/{category_filter_index}/item/{item_index}/hits"
            )

            if item_name and item_hits is not None:
                # Skip the wildcard/any category
                wildcard = self.controller.server.get_message(
                    f"/browser/filter/{category_filter_index}/wildcard"
                )
                if item_name != wildcard:
                    category_counts[item_name] = item_hits
                    logger.info(f"Category '{item_name}' has {item_hits} items")

        return category_counts

    async def collect_browser_metadata(self) -> List[BrowserItem]:
        """Collect metadata for all items in the browser.

        This navigates through the browser and collects metadata for each item,
        using pagination to access all available results beyond the 16-item limit.

        Returns:
            List of BrowserItem objects with metadata
        """
        if self.client is None:
            logger.error("Client not initialized")
            return []

        # Navigate to the Result tab (previously called "Everything" tab)
        if not await self.navigate_to_everything_tab():
            logger.error("Failed to navigate to browser tab")
            return []

        # Collect browser items
        browser_items = []
        start_time = time.time()
        logger.info("Beginning metadata collection from browser results...")

        # Use pagination to collect all results
        global_result_index = 0  # To track overall result index across pages
        page_num = 1

        # Instead of a hard limit, continue until we find no more results
        while True:
            logger.info(f"Collecting metadata from page {page_num}...")
            page_start_time = time.time()

            # Check for devices on this page
            page_has_results = False
            page_items = []

            # Process up to 32 items on this page (some versions of Bitwig show more than 16)
            for page_item_index in range(1, 33):
                # Check if this result exists
                result_exists = None
                # Try multiple times to get the result existence
                for retry in range(3):
                    result_exists = self.controller.server.get_message(
                        f"/browser/result/{page_item_index}/exists"
                    )
                    if result_exists is not None:
                        break
                    # Try refreshing the connection
                    self.client.refresh()
                    await asyncio.sleep(0.2)

                if not result_exists:
                    logger.info(
                        f"No more results in page {page_num} after item {page_item_index-1}"
                    )
                    break

                # We have at least one result on this page
                page_has_results = True
                global_result_index += 1

                # Get result name
                result_name = self.controller.server.get_message(
                    f"/browser/result/{page_item_index}/name"
                )
                if not result_name:
                    logger.warning(
                        f"Result {page_item_index} on page {page_num} has no name"
                    )
                    continue

                # Select the result to view metadata
                logger.info(
                    f"Examining result {global_result_index} (page {page_num}, item {page_item_index}): {result_name}"
                )

                # Directly select this specific result item by sending the OSC command
                # This is more reliable than using relative navigation with "+"
                self.client.send(f"/browser/result/{page_item_index}/select", 1)
                await asyncio.sleep(0.5)  # Increased wait time for selection

                # Collect metadata from filters
                metadata = DeviceMetadata(
                    name=result_name,
                    type="Unknown",  # Default value instead of empty string
                    category="Unknown",  # Default value instead of empty string
                    creator="Unknown",  # Default value instead of empty string
                    tags="",  # Empty string instead of empty list for ChromaDB compatibility
                    description="",  # Empty string instead of None for ChromaDB compatibility
                )

                # Try to extract detailed metadata for this device
                logger.info(f"Collecting metadata for {result_name}")

                # Refresh to ensure we get the latest device info
                self.client.refresh()
                await asyncio.sleep(0.3)

                # First, try to get device info from the result data
                device_type = self.controller.server.get_message(
                    f"/browser/result/{page_item_index}/fileType"
                )
                if device_type:
                    metadata["type"] = device_type
                    logger.info(f"  Device type: {device_type}")

                # Get any product info
                product = self.controller.server.get_message(
                    f"/browser/result/{page_item_index}/product"
                )
                if product:
                    metadata["creator"] = product
                    logger.info(f"  Product: {product}")

                # Get file info like path
                file_path = self.controller.server.get_message(
                    f"/browser/result/{page_item_index}/path"
                )
                if file_path:
                    # Try to extract more info from the path
                    if "Bitwig Studio" in file_path:
                        metadata["creator"] = "Bitwig"
                    # Extract directory components for category info
                    path_parts = file_path.split("/")
                    if len(path_parts) > 2:
                        # Usually the last folder is a good category
                        potential_category = path_parts[-2]
                        if potential_category not in ["Presets", "Library", "Content"]:
                            metadata["category"] = potential_category
                            logger.info(f"  Category from path: {potential_category}")
                    logger.info(f"  Path: {file_path}")

                # If we still don't have good metadata, check the filters
                if (
                    metadata["type"] == "Unknown"
                    or metadata["category"] == "Unknown"
                    or metadata["creator"] == "Unknown"
                ):
                    logger.info("  Checking filters for additional metadata...")

                    for filter_index in range(1, 7):  # Up to 6 filters
                        filter_exists = self.controller.server.get_message(
                            f"/browser/filter/{filter_index}/exists"
                        )
                        if not filter_exists:
                            continue

                        filter_name = self.controller.server.get_message(
                            f"/browser/filter/{filter_index}/name"
                        )
                        if not filter_name:
                            continue

                        # Skip the "Any X" filters since they don't give useful metadata
                        if filter_name.lower() in [
                            "location",
                            "tags",
                            "device type",
                            "file type",
                        ]:
                            continue

                        logger.info(f"  Filter {filter_index}: {filter_name}")

                        # First, try to directly get the selected item
                        selected_item_name = self.controller.server.get_message(
                            f"/browser/filter/{filter_index}/selectedItemName"
                        )

                        if (
                            selected_item_name
                            and selected_item_name != f"Any {filter_name}"
                        ):
                            logger.info(f"    Selected item: {selected_item_name}")
                            item_name = selected_item_name

                            # Map filter name to metadata field
                            if (
                                filter_name.lower() == "category"
                                and metadata["category"] == "Unknown"
                            ):
                                metadata["category"] = item_name
                                logger.info(f"    - Category: {item_name}")
                            elif (
                                filter_name.lower() == "creator"
                                and metadata["creator"] == "Unknown"
                            ):
                                metadata["creator"] = item_name
                                logger.info(f"    - Creator: {item_name}")
                            elif (
                                filter_name.lower() == "type"
                                and metadata["type"] == "Unknown"
                            ):
                                metadata["type"] = item_name
                                logger.info(f"    - Type: {item_name}")
                            elif filter_name.lower() == "tags":
                                # Append to tags string with comma separator
                                if metadata["tags"]:
                                    metadata["tags"] += f", {item_name}"
                                else:
                                    metadata["tags"] = item_name
                                logger.info(f"    - Tag: {item_name}")

                # Try to get more device info through other OSC paths

                # Get device name without prefix/suffix
                if "(" in result_name and ")" in result_name:
                    # Strip out anything in parentheses
                    import re

                    clean_name = re.sub(r"\([^)]*\)", "", result_name).strip()
                    if clean_name:
                        metadata["clean_name"] = clean_name

                # If we still have "Unknown" fields, try to determine from the name
                if metadata["type"] == "Unknown":
                    # Make educated guesses based on device name
                    if any(
                        x in result_name
                        for x in [
                            "Synth",
                            "Piano",
                            "Bass",
                            "Poly",
                            "Lead",
                            "Sampler",
                            "XY",
                        ]
                    ):
                        metadata["type"] = "Instrument"
                    elif any(
                        x in result_name
                        for x in ["FX", "Delay", "Reverb", "Chorus", "EQ", "Compressor"]
                    ):
                        metadata["type"] = "Audio Effect"
                    elif any(x in result_name for x in ["Note", "Arp", "Chord"]):
                        metadata["type"] = "Note Effect"

                # Final log of collected metadata
                logger.info(f"  Final metadata for {result_name}:")
                logger.info(f"    Type: {metadata['type']}")
                logger.info(f"    Category: {metadata['category']}")
                logger.info(f"    Creator: {metadata['creator']}")
                logger.info(f"    Tags: {metadata['tags']}")

                # Add the item to our collection
                browser_item = BrowserItem(
                    name=result_name, metadata=metadata, index=global_result_index
                )
                browser_items.append(browser_item)
                page_items.append(browser_item)

                logger.info(
                    f"Collected metadata for: {result_name} [{metadata.get('type', 'Unknown')}] - {metadata.get('category', 'Unknown')} by {metadata.get('creator', 'Unknown')}"
                )

            # Show progress for this page
            page_time = time.time() - page_start_time
            logger.info(
                f"Collected {len(page_items)} items from page {page_num} in {page_time:.1f}s"
            )

            # Show overall progress
            total_elapsed = time.time() - start_time
            items_per_second = (
                global_result_index / total_elapsed if total_elapsed > 0 else 0
            )
            logger.info(
                f"Overall progress: {global_result_index} items in {total_elapsed:.1f}s ({items_per_second:.2f} items/s)"
            )

            # If this page had no results, we've reached the end
            if not page_has_results:
                logger.info(
                    f"No devices found on page {page_num}, reached end of results"
                )
                break

            # We always continue to the next page, even if we found fewer than 16 items
            # Bitwig sometimes uses different page sizes or may have partial pages
            # We let the existence check on next page determine if we're done

            # Increment page number for the next iteration
            page_num += 1

            # Check if we hit repeat - store the current page's results for comparison
            if not page_items:
                # If no items on this page, we're done
                logger.info("No items on this page, finished collecting")
                break

            # Store the first 3 items on this page for comparison
            current_page_first_items = [
                item.name for item in page_items[: min(3, len(page_items))]
            ]
            logger.info(f"First 3 items on current page: {current_page_first_items}")

            # Navigate to the next page
            logger.info(f"Moving to page {page_num}...")

            # Directly send both page navigation commands for better reliability
            self.client.send("/browser/page/+", 1)  # Alternative command
            await asyncio.sleep(0.5)
            self.client.select_next_browser_result_page()  # Standard command
            await asyncio.sleep(2.0)  # Give more time for page to load

            # Refresh after page navigation
            self.client.refresh()
            await asyncio.sleep(1.0)

            # Check if we actually moved to a new page by checking the first 3 results
            first_results_on_new_page = []
            for i in range(1, 4):  # Check first 3 items
                result_name = self.controller.server.get_message(
                    f"/browser/result/{i}/name"
                )
                if result_name:
                    first_results_on_new_page.append(result_name)

            logger.info(f"First 3 items on new page: {first_results_on_new_page}")

            # If all first results on new page match first results on previous page,
            # we're likely at the end of the collection or have a pagination issue
            if (
                len(first_results_on_new_page) >= 1
                and len(current_page_first_items) >= 1
            ):
                if first_results_on_new_page[0] == current_page_first_items[0]:
                    logger.info(
                        "First result on new page matches first result of previous page, finished collecting"
                    )
                    break

        # Cancel the browser session
        logger.info("Closing browser session...")
        self.client.cancel_browser()

        total_time = time.time() - start_time
        logger.info(
            f"Metadata collection complete: {len(browser_items)} items in {total_time:.1f}s"
        )

        return browser_items

    async def index_browser_content(self) -> None:
        """Index all browser content into the vector database."""
        try:
            # Only initialize controller if we don't already have one
            if self.controller is None:
                logger.info("Initializing OSC controller to communicate with Bitwig...")
                controller_initialized = await self.initialize_controller()

                if not controller_initialized:
                    logger.error(
                        "Failed to initialize OSC controller. Is Bitwig Studio running?"
                    )
                    logger.error(
                        "Please make sure Bitwig Studio is running and try again."
                    )
                    return
            else:
                logger.info("Using existing OSC controller")
                # Refresh the existing controller to make sure it's responsive
                try:
                    self.client.refresh()
                    await asyncio.sleep(1.0)
                except Exception as e:
                    logger.warning(f"Error refreshing existing controller: {e}")

            # Check if we have a client before proceeding
            if not self.client:
                logger.error(
                    "OSC client is not available. Cannot communicate with Bitwig."
                )
                return

            # First, try to get an estimate of the total number of browser items
            # This helps us understand the scale of the indexing job
            logger.info("=" * 60)
            logger.info("Checking total browser items from the 'Everything' tab...")
            total_items_estimate = await self.check_total_browser_items()

            if total_items_estimate > 0:
                logger.info(f"Estimated total browser items: {total_items_estimate}")

                # Also get item counts by category
                logger.info("Checking item counts by category...")
                category_counts = await self.check_item_counts_by_category()
                if category_counts:
                    logger.info("Items by category:")
                    for category, count in sorted(
                        category_counts.items(), key=lambda x: x[1], reverse=True
                    ):
                        logger.info(f"  {category}: {count} items")
            else:
                logger.warning("Could not get an estimate of total browser items")

            # Find all browser tabs
            logger.info("=" * 60)
            logger.info("Mapping browser tabs...")
            all_tabs = await self.navigate_browser_tabs()

            if not all_tabs:
                logger.error(
                    "No browser tabs found. Please check if:"
                    "\n1. Bitwig Studio is running with a project open"
                    "\n2. The OSC Controller extension is enabled in Bitwig settings"
                    "\n3. The correct ports are configured (8000 for sending to Bitwig, 9000 for receiving)"
                    "\n4. No other applications are using the same ports"
                )
                return

            logger.info(f"Will index content from {len(all_tabs)} browser tabs")

            # Process each tab - prioritizing main device tabs first
            # Reorder tabs to process main device tabs first
            priority_tabs = [
                "Instruments",
                "Audio FX",
                "Note FX",
                "Containers",
                "Modulators",
            ]
            reordered_tabs = []
            other_tabs = []

            for tab_name in all_tabs:
                if tab_name in priority_tabs:
                    reordered_tabs.append(tab_name)
                else:
                    other_tabs.append(tab_name)

            # Add remaining tabs
            reordered_tabs.extend(other_tabs)

            # Try to set up browser contexts if we didn't inherit them
            contexts = {}
            controller_exists = hasattr(self, 'controller') and self.controller is not None
            if controller_exists:
                logger.info("Setting up browser contexts to access different tabs...")
                contexts = await setup_browser_contexts(self.controller)
                if contexts:
                    logger.info(f"Successfully set up {len(contexts)} browser contexts")
                    for context, tab in contexts.items():
                        logger.info(f"  {context} context opens tab: {tab}")
                else:
                    logger.warning(
                        "Failed to set up browser contexts. Will proceed with standard navigation only."
                    )

            # Process each tab
            all_browser_items = []

            for tab_index, tab_name in enumerate(reordered_tabs, 1):
                logger.info("=" * 60)
                logger.info(
                    f"Processing tab {tab_index}/{len(reordered_tabs)}: {tab_name}"
                )
                logger.info("=" * 60)

                # Try to navigate to this tab using context if available
                tab_navigated = False

                # Check if we have a context for this tab
                for context_name, context_tab in contexts.items():
                    if context_tab == tab_name:
                        logger.info(
                            f"Using '{context_name}' context to access '{tab_name}' tab"
                        )

                        # Apply the right context based on name
                        if context_name == "instrument_track":
                            # Select instrument track
                            self.client.send("/track/1/select", 1)
                            await asyncio.sleep(1.0)
                            # Open browser
                            self.client.browse_for_device("after")
                            await asyncio.sleep(1.0)

                        elif context_name == "audio_track":
                            # Select audio track
                            self.client.send("/track/2/select", 1)
                            await asyncio.sleep(1.0)
                            # Open browser
                            self.client.browse_for_device("after")
                            await asyncio.sleep(1.0)

                        elif context_name == "before_instrument":
                            # Select instrument track
                            self.client.send("/track/1/select", 1)
                            await asyncio.sleep(1.0)
                            # Open browser before the first device
                            self.client.browse_for_device("before")
                            await asyncio.sleep(1.0)

                        # Verify we got the right tab
                        current_tab = self.controller.server.get_message("/browser/tab")
                        if current_tab == tab_name:
                            logger.info(
                                f"Successfully navigated to '{tab_name}' tab using context"
                            )
                            tab_navigated = True
                            break
                        else:
                            logger.warning(
                                f"Context navigation failed: expected '{tab_name}' but got '{current_tab}'"
                            )
                            # Cancel browser and try again with standard navigation
                            self.client.cancel_browser()
                            await asyncio.sleep(1.0)

                # If context navigation failed, try standard tab navigation
                if not tab_navigated:
                    logger.info(f"Using standard navigation to reach '{tab_name}' tab")
                    if not await self.navigate_to_tab(tab_name):
                        logger.warning(
                            f"Could not navigate to '{tab_name}' tab, skipping"
                        )
                        continue

                # Collect metadata from this tab
                logger.info(f"Collecting metadata from '{tab_name}' tab...")
                start_time = time.time()
                tab_items = await self.collect_browser_metadata()
                collection_time = time.time() - start_time

                # Add tab name to each item's metadata for better categorization
                for item in tab_items:
                    item.metadata["source_tab"] = tab_name

                    # If type is Unknown but we have a tab name, use it as a hint
                    # For example, if we're in the "Instruments" tab, items are likely instruments
                    if item.metadata["type"] == "Unknown" and tab_name:
                        if tab_name in [
                            "Instruments",
                            "Instrument",
                            "Synths",
                            "Sampler",
                        ]:
                            item.metadata["type"] = "Instrument"
                        elif tab_name in ["Audio FX", "Effects", "FX"]:
                            item.metadata["type"] = "Audio Effect"
                        elif tab_name in ["Note FX", "MIDI FX"]:
                            item.metadata["type"] = "MIDI Effect"
                        elif tab_name in ["Containers", "Container", "Chain"]:
                            item.metadata["type"] = "Container"
                        elif tab_name in ["Modulators", "Modulator"]:
                            item.metadata["type"] = "Modulator"

                # Add these items to our global collection
                all_browser_items.extend(tab_items)

                logger.info(
                    f"Collected {len(tab_items)} items from '{tab_name}' tab in {collection_time:.1f}s"
                )
                logger.info(f"Total items collected so far: {len(all_browser_items)}")

                # Check collection progress (compare with estimates if available)
                if total_items_estimate > 0:
                    progress_percent = (
                        len(all_browser_items) / total_items_estimate * 100
                    )
                    logger.info(
                        f"Overall progress: approximately {progress_percent:.1f}% complete"
                    )

            # Log overall collection result
            logger.info("=" * 60)
            logger.info(
                f"Finished collecting {len(all_browser_items)} items from all tabs"
            )
            if total_items_estimate > 0:
                coverage_percent = len(all_browser_items) / total_items_estimate * 100
                logger.info(
                    f"Coverage: approximately {coverage_percent:.1f}% of estimated total items"
                )
            logger.info("=" * 60)

            if not all_browser_items:
                logger.error(
                    "No items were collected. Is Bitwig Studio running with a project open?"
                )
                return

            # Create embeddings and add to collection - process in chunks to avoid memory issues
            logger.info("=" * 60)
            logger.info("Creating embeddings and adding to collection...")
            logger.info(
                "This may take a few minutes depending on the number of devices..."
            )
            logger.info("=" * 60)

            # Process in chunks to avoid memory issues
            chunk_size = 500  # Process 500 items at a time
            embedding_start = time.time()
            total_added = 0

            # Make sure we have items to process
            if not all_browser_items:
                logger.warning(
                    "No items to add to database - collection will be empty."
                )
                return

            for chunk_index in range(0, len(all_browser_items), chunk_size):
                chunk_items = all_browser_items[chunk_index : chunk_index + chunk_size]
                chunk_start = time.time()

                logger.info(
                    f"Processing chunk {chunk_index//chunk_size + 1}/{(len(all_browser_items) + chunk_size - 1)//chunk_size}"
                )
                logger.info(f"Items in this chunk: {len(chunk_items)}")

                # Prepare batch data for this chunk
                ids = []
                embeddings = []
                metadatas = []
                documents = []

                # Process each item in the chunk
                for i, item in enumerate(chunk_items):
                    # Create unique ID
                    item_id = f"device_{chunk_index + i + 1}"
                    ids.append(item_id)

                    # Create search text and embedding
                    search_text = self.create_search_text(item)
                    logger.debug(f"Search text for {item.name}: {search_text[:100]}...")

                    embedding = self.create_embedding(search_text)

                    # Sanitize metadata for ChromaDB compatibility
                    # ChromaDB requires all metadata values to be str, int, float, or bool
                    sanitized_metadata = {}
                    for key, value in item.metadata.items():
                        if value is None:
                            # Replace None with empty string
                            sanitized_metadata[key] = ""
                        elif isinstance(value, (str, int, float, bool)):
                            # These types are already ChromaDB-compatible
                            sanitized_metadata[key] = value
                        else:
                            # Convert any other types to string
                            sanitized_metadata[key] = str(value)

                    # Add to batch
                    embeddings.append(embedding)
                    metadatas.append(sanitized_metadata)
                    documents.append(search_text)

                    # Log progress for every few items or at the end
                    embedding_batch_size = 20  # Log every 20 items
                    if (i + 1) % embedding_batch_size == 0 or i == len(chunk_items) - 1:
                        # Calculate progress within this chunk
                        chunk_progress = (i + 1) / len(chunk_items) * 100

                        # Calculate overall progress
                        total_progress = (
                            (chunk_index + i + 1) / len(all_browser_items) * 100
                        )

                        # Calculate time metrics
                        # Skip chunk timing
                        total_elapsed = time.time() - embedding_start
                        items_per_second = (
                            (chunk_index + i + 1) / total_elapsed
                            if total_elapsed > 0
                            else 0
                        )

                        # Calculate ETA
                        remaining_items = len(all_browser_items) - (chunk_index + i + 1)
                        eta_minutes = (
                            remaining_items / items_per_second / 60
                            if items_per_second > 0
                            else 0
                        )

                        logger.info(
                            f"Chunk: {chunk_progress:.1f}% - "
                            f"Overall: {total_progress:.1f}% ({chunk_index + i + 1}/{len(all_browser_items)}) - "
                            f"Rate: {items_per_second:.2f} items/s - "
                            f"ETA: {eta_minutes:.1f} minutes"
                        )

                # Add this chunk's items to the collection
                logger.info(f"Adding {len(chunk_items)} items to vector database...")
                chunk_add_start = time.time()

                try:
                    # Validate metadata before adding (debug info)
                    invalid_metadata = []
                    for i, metadata in enumerate(metadatas):
                        for key, value in metadata.items():
                            if not isinstance(value, (str, int, float, bool)):
                                invalid_metadata.append((i, key, type(value), value))

                    if invalid_metadata:
                        logger.error(
                            f"Found {len(invalid_metadata)} invalid metadata values:"
                        )
                        for idx, key, val_type, val in invalid_metadata[
                            :5
                        ]:  # Show first 5 only
                            logger.error(
                                f"  Item {idx}, key '{key}': {val_type} = {val}"
                            )
                        # Fix them in place
                        for idx, key, _, _ in invalid_metadata:
                            metadatas[idx][key] = (
                                str(metadatas[idx][key])
                                if metadatas[idx][key] is not None
                                else ""
                            )
                        logger.info(
                            "Fixed invalid metadata values - continuing with add"
                        )

                    # Add the chunk to ChromaDB
                    self.collection.add(
                        ids=ids,
                        embeddings=embeddings,
                        metadatas=metadatas,
                        documents=documents,
                    )

                    total_added += len(chunk_items)
                    chunk_add_time = time.time() - chunk_add_start
                    logger.info(f"Chunk added in {chunk_add_time:.1f}s")

                except Exception as e:
                    logger.error(f"Error adding chunk to database: {e}")
                    logger.error(
                        "This is likely due to incompatible metadata types in ChromaDB"
                    )
                    logger.error(
                        "The script will continue with the next chunk if possible"
                    )
                    # Continue with the next chunk instead of failing completely

                chunk_time = time.time() - chunk_start
                logger.info(f"Chunk processed in {chunk_time:.1f}s")
                logger.info(f"Total items added so far: {total_added}")

            total_time = time.time() - embedding_start
            logger.info("=" * 60)
            logger.info(f"Successfully indexed {total_added} browser items")
            logger.info(f"Total indexing time: {total_time:.1f}s")
            logger.info(f"Average rate: {total_added/total_time:.2f} items/s")
            logger.info("=" * 60)

        except Exception as e:
            logger.exception(f"Error during indexing: {str(e)}")
            raise

        finally:
            # Close the controller
            logger.info("Closing OSC controller...")
            await self.close_controller()

    def search_devices(
        self,
        query: str,
        n_results: int = 5,
        filter_options: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Search for devices by semantic similarity.

        Args:
            query: Natural language query
            n_results: Number of results to return
            filter_options: Optional filters for metadata (e.g., {"category": "EQ"})

        Returns:
            List of search results with metadata
        """
        # Create embedding for the query
        query_embedding = self.create_embedding(query)

        # Prepare filter if provided
        where_filter = filter_options if filter_options else None

        # Perform the search
        results = self.collection.query(
            query_embeddings=[query_embedding], n_results=n_results, where=where_filter
        )

        # Format results
        formatted_results = []
        if results["ids"]:
            for i, item_id in enumerate(results["ids"][0]):
                formatted_results.append(
                    {
                        "id": item_id,
                        "name": results["metadatas"][0][i]["name"],
                        "type": results["metadatas"][0][i]["type"],
                        "category": results["metadatas"][0][i]["category"],
                        "creator": results["metadatas"][0][i]["creator"],
                        "tags": results["metadatas"][0][i].get("tags", []),
                        "description": results["metadatas"][0][i].get(
                            "description", ""
                        ),
                        "document": results["documents"][0][i],
                        "distance": results["distances"][0][i]
                        if "distances" in results
                        else None,
                    }
                )

        return formatted_results

    def get_device_count(self) -> int:
        """Get the number of devices in the index."""
        return self.collection.count()

    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the collection."""
        count = self.collection.count()

        # Get unique categories, types, and creators
        results = self.collection.get()

        categories = set()
        types = set()
        creators = set()

        # Count entries with descriptions
        with_description = 0
        without_description = 0

        if results["metadatas"]:
            for metadata in results["metadatas"]:
                if "category" in metadata and metadata["category"]:
                    categories.add(metadata["category"])

                if "type" in metadata and metadata["type"]:
                    types.add(metadata["type"])

                if "creator" in metadata and metadata["creator"]:
                    creators.add(metadata["creator"])

                # Check for description presence
                if "description" in metadata and metadata["description"]:
                    with_description += 1
                else:
                    without_description += 1

        return {
            "count": count,
            "with_description": with_description,
            "without_description": without_description,
            "description_percentage": (with_description / count * 100)
            if count > 0
            else 0,
            "categories": sorted(list(categories)),
            "types": sorted(list(types)),
            "creators": sorted(list(creators)),
        }


async def create_track_with_context(controller, track_type="instrument", position=1):
    """Create a track of a specific type to set up the right browser context.

    Args:
        controller: BitwigOSCController instance
        track_type: Type of track to create ("instrument", "audio", "effect")
        position: Position to insert the track (1-based)

    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info(f"Creating {track_type} track at position {position}...")

        # Map track type to OSC command
        track_command = "/track/add/"
        if track_type.lower() == "instrument":
            track_command += "instrument"
        elif track_type.lower() == "audio":
            track_command += "audio"
        elif track_type.lower() == "effect":
            track_command += "effect"
        else:
            logger.error(f"Unknown track type: {track_type}")
            return False

        # Add the track
        controller.client.send(track_command, position)
        await asyncio.sleep(2.0)  # Give Bitwig time to create the track

        # Verify the track was created by checking if we have a track at the position
        track_name = controller.server.get_message(f"/track/{position}/name")
        if track_name:
            logger.info(f"Successfully created {track_type} track: {track_name}")
            return True
        else:
            logger.warning(
                f"Failed to create {track_type} track or verify its creation"
            )
            return False

    except Exception as e:
        logger.error(f"Error creating track: {e}")
        return False


async def setup_browser_contexts(controller):
    """Set up different browser contexts to access different browser tabs.

    Args:
        controller: BitwigOSCController instance

    Returns:
        Dictionary mapping context names to browser tabs
    """
    contexts = {}

    try:
        # Create an instrument track for instrument browser context
        instrument_track_created = await create_track_with_context(
            controller, "instrument", 1
        )
        if instrument_track_created:
            # Select the track
            controller.client.send("/track/1/select", 1)
            await asyncio.sleep(1.0)

            # Open browser to test context
            controller.client.browse_for_device("after")
            await asyncio.sleep(1.0)

            tab = controller.server.get_message("/browser/tab")
            if tab:
                contexts["instrument_track"] = tab
                logger.info(f"Instrument track context opens tab: {tab}")

            # Cancel browser
            controller.client.cancel_browser()
            await asyncio.sleep(1.0)

        # Create an audio track for audio effect browser context
        audio_track_created = await create_track_with_context(controller, "audio", 2)
        if audio_track_created:
            # Select the track
            controller.client.send("/track/2/select", 1)
            await asyncio.sleep(1.0)

            # Open browser to test context
            controller.client.browse_for_device("after")
            await asyncio.sleep(1.0)

            tab = controller.server.get_message("/browser/tab")
            if tab:
                contexts["audio_track"] = tab
                logger.info(f"Audio track context opens tab: {tab}")

            # Cancel browser
            controller.client.cancel_browser()
            await asyncio.sleep(1.0)

        # Try different positions in the instrument track
        if instrument_track_created:
            # Select the track
            controller.client.send("/track/1/select", 1)
            await asyncio.sleep(1.0)

            # Try to add a device to create a device chain
            controller.client.browse_for_device("after")
            await asyncio.sleep(1.0)

            # Navigate to Instruments tab explicitly
            instrument_tab_found = False
            for _ in range(10):  # Try up to 10 times
                current_tab = controller.server.get_message("/browser/tab")
                if current_tab in ["Instruments", "Instrument"]:
                    instrument_tab_found = True
                    break
                controller.client.navigate_browser_tab("+")
                await asyncio.sleep(0.5)

            if instrument_tab_found:
                # Select first instrument
                controller.client.select_next_browser_result()
                await asyncio.sleep(0.5)
                controller.client.commit_browser_selection()
                await asyncio.sleep(1.0)

                # Now try opening browser in different positions
                controller.client.browse_for_device("before")
                await asyncio.sleep(1.0)

                tab = controller.server.get_message("/browser/tab")
                if tab:
                    contexts["before_instrument"] = tab
                    logger.info(f"Before instrument context opens tab: {tab}")

                controller.client.cancel_browser()
                await asyncio.sleep(1.0)

        return contexts

    except Exception as e:
        logger.error(f"Error setting up browser contexts: {e}")
        return contexts


async def build_index(persistent_dir: str = None, existing_controller=None):
    """Build the browser index as a standalone utility.

    Args:
        persistent_dir: Directory to store the ChromaDB persistent data
        existing_controller: Optional existing OSC controller to reuse

    Returns:
        BitwigBrowserIndexer instance or None if the indexing failed
    """
    # If no directory specified, use the project data directory
    if persistent_dir is None:
        persistent_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "data",
            "browser_index",
        )

    # Ensure directory exists
    os.makedirs(persistent_dir, exist_ok=True)

    # Configure more detailed logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(os.path.join(persistent_dir, "indexer.log")),
        ],
    )

    logger.info("=" * 80)
    logger.info("Starting browser indexing process")
    logger.info(f"Persistent directory: {persistent_dir}")
    logger.info("=" * 80)

    indexer = None
    should_close_controller = existing_controller is None
    try:
        # Initialize the indexer
        indexer = BitwigBrowserIndexer(persistent_dir=persistent_dir)

        # If we have an existing controller, use it
        if existing_controller:
            logger.info("Using existing OSC controller")
            indexer.controller = existing_controller
            indexer.client = existing_controller.client
        else:
            # Initialize our own controller
            controller_initialized = await indexer.initialize_controller()
            if not controller_initialized:
                logger.error(
                    "Failed to initialize OSC controller. Cannot proceed with indexing."
                )
                return None

        # Try to set up different browser contexts to access different tabs
        logger.info("Setting up browser contexts to access different tabs...")
        contexts = await setup_browser_contexts(indexer.controller)
        if contexts:
            logger.info(f"Successfully set up {len(contexts)} browser contexts")
            for context, tab in contexts.items():
                logger.info(f"  {context} context opens tab: {tab}")
        else:
            logger.warning(
                "Failed to set up browser contexts. Will proceed with standard indexing."
            )

        # Perform indexing
        await indexer.index_browser_content()

        # Only get statistics if we have items
        if indexer.get_device_count() > 0:
            # Print statistics
            stats = indexer.get_collection_stats()
            logger.info(f"Index statistics: {json.dumps(stats, indent=2)}")
            logger.info("Browser indexing complete")
        else:
            logger.warning("No devices were indexed. The collection may be empty.")

    except Exception as e:
        logger.exception(f"Error during indexing: {e}")
        if indexer is not None and should_close_controller:
            try:
                # Try to close the controller even if an error occurred,
                # but only if we created it ourselves
                await indexer.close_controller()
            except Exception:
                pass
        return None

    # Don't close the controller if we're using an existing one
    if indexer is not None and should_close_controller:
        await indexer.close_controller()

    return indexer


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
                device_url = urljoin(self.base_url, link["href"])

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

    Returns:
        Number of devices that were enhanced with descriptions
    """
    # If no directory specified, use the project data directory
    if persistent_dir is None:
        persistent_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "data",
            "browser_index",
        )

    logger.info("=" * 80)
    logger.info("Starting index enhancement process")
    logger.info(f"Persistent directory: {persistent_dir}")
    logger.info("=" * 80)

    # Initialize the indexer with the existing data
    indexer = BitwigBrowserIndexer(persistent_dir=persistent_dir)

    # Check if the index exists
    if indexer.get_device_count() == 0:
        logger.error(
            f"No index found in {persistent_dir}. Please run build_index first."
        )
        return 0

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
    return updated_count


async def build_and_enhance_index(persistent_dir: str = None, existing_controller=None):
    """Build the browser index and enhance it with descriptions.

    This is a convenience function that runs both indexing and enhancement.

    Args:
        persistent_dir: Directory to store the ChromaDB persistent data
        existing_controller: Optional existing OSC controller to reuse

    Returns:
        BitwigBrowserIndexer instance or None if the indexing failed
    """
    # Build the index first
    indexer = await build_index(persistent_dir, existing_controller)

    if indexer is None:
        logger.error("Index building failed, skipping enhancement")
        return None

    # Enhance the index with descriptions
    await enhance_index_with_descriptions(persistent_dir)

    return indexer


if __name__ == "__main__":
    """Run the indexer as a standalone script."""
    import argparse

    parser = argparse.ArgumentParser(description="Bitwig Browser Indexer and Enhancer")
    parser.add_argument(
        "--persistent-dir",
        default=None,
        help="Directory where the vector database is stored (default: project's data/browser_index)",
    )
    parser.add_argument(
        "--enhance-only",
        action="store_true",
        help="Only enhance the existing index with descriptions, don't rebuild",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Build the index and enhance it with descriptions",
    )

    args = parser.parse_args()

    if args.enhance_only:
        asyncio.run(enhance_index_with_descriptions(args.persistent_dir))
    elif args.full:
        asyncio.run(build_and_enhance_index(args.persistent_dir))
    else:
        asyncio.run(build_index(args.persistent_dir))
