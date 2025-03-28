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
    tags: List[str]
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
                self.controller = BitwigOSCController()

                # Check if controller was created successfully
                if not self.controller:
                    logger.error("Failed to create OSC controller")
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
                    # Try to continue anyway

                # Connect to Bitwig
                logger.info("Waiting for Bitwig Studio connection...")
                await asyncio.sleep(2.0)  # Give more time for connection

                # Refresh the controller to get initial state
                logger.info("Refreshing controller state...")
                self.client.refresh()
                await asyncio.sleep(2.0)  # Wait longer for responses

                # Check if we're receiving data from Bitwig
                logger.info("Checking Bitwig Studio connection...")
                # Try to get basic transport info
                self.client.refresh()
                await asyncio.sleep(1.0)

                # Try to get a basic response from Bitwig to verify connection
                tempo = self.controller.server.get_message("/transport/tempo")
                if tempo is None:
                    logger.warning("No response received from Bitwig Studio")
                    browser_exists = self.controller.server.get_message(
                        "/browser/exists"
                    )
                    if browser_exists is None:
                        logger.warning(
                            "Browser not available - Bitwig may not be responding properly"
                        )
                        # Still continue as we might still be able to browse

                return True
            return True
        except Exception as e:
            logger.exception(f"Error initializing controller: {e}")
            return False

    async def close_controller(self) -> None:
        """Close the OSC controller."""
        try:
            if self.controller is not None:
                self.controller.stop()  # This is a synchronous method
        except Exception as e:
            logger.warning(f"Error closing controller: {e}")
        finally:
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
        tags_text = ", ".join(metadata["tags"]) if metadata.get("tags") else ""
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

    async def navigate_to_everything_tab(self) -> bool:
        """Navigate to the 'Result' tab in the browser.

        Returns:
            True if successfully navigated, False otherwise
        """
        if self.client is None:
            logger.error("Client not initialized")
            return False

        # First, open the browser
        logger.info("Opening Bitwig browser for device...")
        self.client.browse_for_device("after")
        await asyncio.sleep(1.0)  # Increased wait time for browser to open

        # Check if browser is active
        browser_active = self.controller.server.get_message("/browser/isActive")
        logger.info(f"Browser active: {browser_active}")
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

        # If not on the right tab, try to navigate to it
        max_attempts = 10
        logger.info("Looking for 'Result' or 'Everything' tab...")

        for attempt in range(max_attempts):
            # Navigate to the next tab
            logger.info("Navigating to next tab...")
            self.client.navigate_browser_tab("+")
            await asyncio.sleep(0.5)

            current_tab = self.controller.server.get_message("/browser/tab")
            logger.info(
                f"Current browser tab ({attempt+1}/{max_attempts}): {current_tab}"
            )

            if current_tab == "Result" or current_tab == "Everything":
                logger.info(f"Successfully navigated to '{current_tab}' tab")
                return True

        logger.warning(
            "Could not find 'Result' or 'Everything' tab after multiple attempts"
        )
        # Let's try to continue anyway, as the browser is active
        return True

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
        max_pages = 50  # Safety limit to prevent infinite loops
        global_result_index = 0  # To track overall result index across pages

        for page_num in range(1, max_pages + 1):
            logger.info(f"Collecting metadata from page {page_num}...")
            page_start_time = time.time()

            # Check for devices on this page
            page_has_results = False
            page_items = []

            # Process up to 16 items on this page
            for page_item_index in range(1, 17):
                # Check if this result exists
                result_exists = self.controller.server.get_message(
                    f"/browser/result/{page_item_index}/exists"
                )
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
                self.client.navigate_browser_result("+")
                await asyncio.sleep(0.3)  # Increased wait time for selection

                # Collect metadata from filters
                metadata = DeviceMetadata(
                    name=result_name,
                    type="",
                    category="",
                    creator="",
                    tags=[],
                    description=None,
                )

                # Extract metadata from filters
                # Typically, filter 1 might be creator, filter 2 category, etc.
                logger.debug(f"Collecting filter data for {result_name}")

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

                    logger.debug(f"Filter {filter_index}: {filter_name}")

                    # Get the selected item for this filter
                    for item_index in range(1, 17):  # Up to 16 items per filter
                        item_exists = self.controller.server.get_message(
                            f"/browser/filter/{filter_index}/item/{item_index}/exists"
                        )
                        if not item_exists:
                            break

                        item_selected = self.controller.server.get_message(
                            f"/browser/filter/{filter_index}/item/{item_index}/isSelected"
                        )
                        if not item_selected:
                            continue

                        item_name = self.controller.server.get_message(
                            f"/browser/filter/{filter_index}/item/{item_index}/name"
                        )
                        if not item_name:
                            continue

                        # Map filter name to metadata field
                        if filter_name.lower() == "category":
                            metadata["category"] = item_name
                            logger.debug(f"  - Category: {item_name}")
                        elif filter_name.lower() == "creator":
                            metadata["creator"] = item_name
                            logger.debug(f"  - Creator: {item_name}")
                        elif filter_name.lower() == "type":
                            metadata["type"] = item_name
                            logger.debug(f"  - Type: {item_name}")
                        elif filter_name.lower() == "tags":
                            metadata["tags"].append(item_name)
                            logger.debug(f"  - Tag: {item_name}")

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

            # If we found fewer than 16 results, this is the last page
            if len(page_items) < 16:
                logger.info(
                    f"Only {len(page_items)} devices on page {page_num}, this is likely the last page"
                )
                break

            # Navigate to the next page
            logger.info(f"Moving to page {page_num + 1}...")
            self.client.select_next_browser_result_page()
            await asyncio.sleep(1.0)  # Give time for page to load

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
            # Initialize the controller
            logger.info("Initializing OSC controller to communicate with Bitwig...")
            controller_initialized = await self.initialize_controller()

            if not controller_initialized:
                logger.error(
                    "Failed to initialize OSC controller. Is Bitwig Studio running?"
                )
                logger.error("Please make sure Bitwig Studio is running and try again.")
                return

            # Check if we have a client before proceeding
            if not self.client:
                logger.error(
                    "OSC client is not available. Cannot communicate with Bitwig."
                )
                return

            # Collect metadata
            logger.info("Collecting browser metadata...")
            start_time = time.time()
            browser_items = await self.collect_browser_metadata()
            collection_time = time.time() - start_time
            logger.info(
                f"Collected metadata for {len(browser_items)} items in {collection_time:.1f}s"
            )

            if not browser_items:
                logger.error(
                    "No items were collected. Is Bitwig Studio running with a project open?"
                )
                return

            # Create embeddings and add to collection
            logger.info("=" * 60)
            logger.info("Creating embeddings and adding to collection...")
            logger.info(
                "This may take a few minutes depending on the number of devices..."
            )
            logger.info("=" * 60)

            # Prepare batch data
            ids = []
            embeddings = []
            metadatas = []
            documents = []

            embedding_start = time.time()
            embedding_batch_size = 5  # Process in small batches for better logging

            for i, item in enumerate(browser_items):
                # Create unique ID
                item_id = f"device_{i+1}"
                ids.append(item_id)

                # Create search text and embedding
                search_text = self.create_search_text(item)
                logger.debug(f"Search text for {item.name}: {search_text[:100]}...")

                embedding = self.create_embedding(search_text)

                # Add to batch
                embeddings.append(embedding)
                metadatas.append(item.metadata)
                documents.append(search_text)

                # Log progress for every batch or at the end
                if (i + 1) % embedding_batch_size == 0 or i == len(browser_items) - 1:
                    # Calculate total elapsed time
                    total_elapsed = time.time() - embedding_start
                    items_per_second = (
                        (i + 1) / total_elapsed if total_elapsed > 0 else 0
                    )
                    eta_seconds = (
                        (len(browser_items) - (i + 1)) / items_per_second
                        if items_per_second > 0
                        else 0
                    )

                    logger.info(
                        f"Processed {i+1}/{len(browser_items)} items "
                        f"({(i+1)/len(browser_items)*100:.1f}%) - "
                        f"Rate: {items_per_second:.2f} items/s - "
                        f"ETA: {eta_seconds/60:.1f} minutes"
                    )

            # Add all items to the collection in a single batch
            logger.info("Adding all items to vector database...")
            add_start = time.time()
            self.collection.add(
                ids=ids, embeddings=embeddings, metadatas=metadatas, documents=documents
            )
            add_time = time.time() - add_start

            total_time = time.time() - start_time
            logger.info("=" * 60)
            logger.info(f"Successfully indexed {len(browser_items)} browser items")
            logger.info(f"Collection time: {collection_time:.1f}s")
            logger.info(f"Embedding time: {add_start - embedding_start:.1f}s")
            logger.info(f"Database add time: {add_time:.1f}s")
            logger.info(f"Total indexing time: {total_time:.1f}s")
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

        if results["metadatas"]:
            for metadata in results["metadatas"]:
                if "category" in metadata and metadata["category"]:
                    categories.add(metadata["category"])

                if "type" in metadata and metadata["type"]:
                    types.add(metadata["type"])

                if "creator" in metadata and metadata["creator"]:
                    creators.add(metadata["creator"])

        return {
            "count": count,
            "categories": sorted(list(categories)),
            "types": sorted(list(types)),
            "creators": sorted(list(creators)),
        }


async def build_index(persistent_dir: str = None):
    """Build the browser index as a standalone utility.

    Args:
        persistent_dir: Directory to store the ChromaDB persistent data

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
    try:
        # Initialize the indexer
        indexer = BitwigBrowserIndexer(persistent_dir=persistent_dir)

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
        if indexer is not None:
            try:
                # Try to close the controller even if an error occurred
                await indexer.close_controller()
            except Exception:
                pass
        return None

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


async def build_and_enhance_index(persistent_dir: str = None):
    """Build the browser index and enhance it with descriptions.

    This is a convenience function that runs both indexing and enhancement.

    Args:
        persistent_dir: Directory to store the ChromaDB persistent data

    Returns:
        BitwigBrowserIndexer instance or None if the indexing failed
    """
    # Build the index first
    indexer = await build_index(persistent_dir)

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
