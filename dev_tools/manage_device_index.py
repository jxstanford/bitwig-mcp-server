#!/usr/bin/env python
"""
Device Index Manager

This script provides a comprehensive interface for managing the Bitwig Studio device index.
It allows you to create, update, query, and analyze the device index used for recommendation
and search functionality.

Features:
- Create a full device index from scratch
- Show detailed statistics about the index
- Search for devices directly from the command line
- Enhance existing index with device descriptions
- Test device recommendations

Prerequisites:
- Bitwig Studio must be running with a project open (for indexing)
- The OSC Controller extension must be enabled in Bitwig
- The virtual environment must be activated with the required dependencies
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path

# Add the project root to the Python path to enable imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bitwig_mcp_server.utils.browser_indexer import (
    BitwigBrowserIndexer,
    build_and_enhance_index,
    build_index,
    enhance_index_with_descriptions,
)
from bitwig_mcp_server.utils.device_recommender import BitwigDeviceRecommender

# Set up colorized logging for better readability
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - \033[1;32m%(levelname)s\033[0m - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


async def verify_bitwig_connection():
    """Verify that Bitwig Studio is running and accessible via OSC.

    Returns:
        tuple: (success, controller) where success is a boolean and controller is
               the BitwigOSCController instance if successful, or None otherwise.
    """
    from bitwig_mcp_server.osc.controller import BitwigOSCController

    logger.info("Verifying connection to Bitwig Studio...")

    controller = BitwigOSCController()
    controller.start()

    try:
        # Wait for connection
        await asyncio.sleep(2.0)

        # Try to get basic data from Bitwig
        controller.client.refresh()
        await asyncio.sleep(1.0)

        # Check if we're receiving data
        tempo = controller.server.get_message("/tempo/raw")
        browser_exists = controller.server.get_message("/browser/exists")

        if tempo is None and browser_exists is None:
            logger.error("❌ Could not connect to Bitwig Studio")
            logger.error(
                "Please make sure Bitwig Studio is running with a project open"
            )
            logger.error("and the OSC Controller extension is enabled")
            controller.stop()
            return False, None

        logger.info(f"✅ Successfully connected to Bitwig Studio (tempo: {tempo} BPM)")

        # Check if a project is open (optional but helpful)
        project_name = controller.server.get_message("/application/projectName")
        if project_name:
            logger.info(f"📂 Current project: {project_name}")

        return True, controller

    except Exception as e:
        logger.error(f"❌ Error connecting to Bitwig Studio: {e}")
        controller.stop()
        return False, None


async def create_full_index(args):
    """Create a full index of Bitwig devices and presets."""
    # Start timing
    start_time = time.time()

    # Determine the data directory
    data_dir = get_data_dir(args)

    logger.info("=" * 80)
    logger.info(f"🔍 Creating device index in: {data_dir}")
    logger.info("=" * 80)

    # Verify Bitwig is running first
    connection_success, controller = await verify_bitwig_connection()
    if not connection_success:
        logger.error("🛑 Cannot proceed without a connection to Bitwig Studio")
        return False

    # Check if we're in skip-existing mode
    if args.skip_existing:
        logger.info("🔄 Will skip existing entries with the same name")
        # We'll handle this in the indexing code by filtering out duplicates

        # Check if index exists
        chroma_db = os.path.join(data_dir, "chroma.sqlite3")
        if not os.path.exists(chroma_db):
            logger.warning("⚠️  No existing index found. Will create a new index.")
        else:
            try:
                # Try to get the current count from ChromaDB
                from chromadb.config import Settings
                import chromadb
                import importlib

                importlib.reload(chromadb)
                client = chromadb.PersistentClient(
                    path=data_dir, settings=Settings(anonymized_telemetry=False)
                )

                # Check if collection exists
                try:
                    collection = client.get_collection(name="bitwig_devices")
                    count = collection.count()
                    logger.info(f"📊 Found existing index with {count} devices")

                    # Get all device names to check for duplicates during indexing
                    if count > 0:
                        try:
                            # In ChromaDB, we can get all items and their metadata
                            results = collection.get()
                            if results and results.get("metadatas"):
                                existing_devices = {
                                    meta.get("name"): idx
                                    for idx, meta in zip(
                                        results["ids"], results["metadatas"]
                                    )
                                    if meta and "name" in meta
                                }
                                logger.info(
                                    f"📝 Found {len(existing_devices)} named devices to check for duplicates"
                                )
                                # We'll use this dict later to detect duplicates
                                setattr(args, "existing_devices", existing_devices)
                        except Exception as e:
                            logger.warning(
                                f"⚠️  Could not get existing device names: {e}"
                            )
                            setattr(args, "existing_devices", {})
                except Exception:
                    logger.warning(
                        "⚠️  No existing collection found. Will create a new index."
                    )
            except Exception as e:
                logger.warning(f"⚠️  Error checking existing index: {e}")

    # Display indexing steps
    logger.info("\n📋 Indexing Process:")
    logger.info("1️⃣  Setting up different browser contexts for comprehensive indexing")
    logger.info("2️⃣  Building base device index from all Bitwig browser tabs")
    logger.info("3️⃣  Enhancing index with device descriptions")
    logger.info("4️⃣  Verifying and displaying index statistics\n")

    try:
        # Modify the indexer's behavior based on the skip-existing flag
        if hasattr(args, "existing_devices") and args.skip_existing:
            # Monkey patch the index_browser_content method to filter existing devices
            from functools import wraps

            # Store the original index_browser_content method reference
            original_indexer_class = BitwigBrowserIndexer
            original_index_browser_content = BitwigBrowserIndexer.index_browser_content

            # Create a wrapper that will filter out duplicates
            @wraps(original_index_browser_content)
            async def index_browser_content_with_skip(self, *args, **kwargs):
                # First, collect all browser items using the original method's logic
                try:
                    # Initialize the controller
                    logger.info(
                        "Initializing OSC controller to communicate with Bitwig..."
                    )
                    controller_initialized = await self.initialize_controller()

                    if not controller_initialized:
                        logger.error(
                            "Failed to initialize OSC controller. Is Bitwig Studio running?"
                        )
                        logger.error(
                            "Please make sure Bitwig Studio is running and try again."
                        )
                        return

                    # Check if we have a client before proceeding
                    if not self.client:
                        logger.error(
                            "OSC client is not available. Cannot communicate with Bitwig."
                        )
                        return

                    # Find all browser tabs
                    logger.info("Mapping browser tabs...")
                    all_tabs = await self.navigate_browser_tabs()

                    if not all_tabs:
                        logger.error(
                            "No browser tabs found. Please check Bitwig Studio."
                        )
                        return

                    logger.info(f"Will index content from {len(all_tabs)} browser tabs")

                    # Process each tab
                    all_browser_items = []

                    for tab_index, tab_name in enumerate(all_tabs, 1):
                        logger.info("=" * 60)
                        logger.info(
                            f"Processing tab {tab_index}/{len(all_tabs)}: {tab_name}"
                        )
                        logger.info("=" * 60)

                        # Navigate to this tab
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

                        # Add these items to our global collection
                        all_browser_items.extend(tab_items)

                        logger.info(
                            f"Collected {len(tab_items)} items from '{tab_name}' tab in {collection_time:.1f}s"
                        )
                        logger.info(
                            f"Total items collected so far: {len(all_browser_items)}"
                        )

                    # Log overall collection result
                    logger.info("=" * 60)
                    logger.info(
                        f"Finished collecting {len(all_browser_items)} items from all tabs"
                    )
                    logger.info("=" * 60)

                    if not all_browser_items:
                        logger.error(
                            "No items were collected. Is Bitwig Studio running with a project open?"
                        )
                        return

                    # Get list of existing device names
                    existing_devices = getattr(args, "existing_devices", {})

                    # Filter out duplicate devices
                    filtered_items = []
                    for item in all_browser_items:
                        device_name = item.metadata.get("name")
                        if device_name in existing_devices:
                            logger.info(f"⏩ Skipping existing device: {device_name}")
                        else:
                            filtered_items.append(item)

                    skipped_count = len(all_browser_items) - len(filtered_items)
                    if skipped_count > 0:
                        logger.info(f"⏩ Skipped {skipped_count} existing devices")
                        logger.info(
                            f"💾 Proceeding with {len(filtered_items)} new devices"
                        )

                    # Continue with indexing the filtered items
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

                    for chunk_index in range(0, len(filtered_items), chunk_size):
                        chunk_items = filtered_items[
                            chunk_index : chunk_index + chunk_size
                        ]
                        chunk_start = time.time()

                        logger.info(
                            f"Processing chunk {chunk_index//chunk_size + 1}/{(len(filtered_items) + chunk_size - 1)//chunk_size}"
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
                            logger.debug(
                                f"Search text for {item.name}: {search_text[:100]}..."
                            )

                            embedding = self.create_embedding(search_text)

                            # Add to batch
                            embeddings.append(embedding)
                            metadatas.append(item.metadata)
                            documents.append(search_text)

                            # Log progress for every few items or at the end
                            embedding_batch_size = 20  # Log every 20 items
                            if (i + 1) % embedding_batch_size == 0 or i == len(
                                chunk_items
                            ) - 1:
                                # Calculate progress within this chunk
                                chunk_progress = (i + 1) / len(chunk_items) * 100

                                # Calculate overall progress
                                total_progress = (
                                    (chunk_index + i + 1) / len(filtered_items) * 100
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
                                remaining_items = len(filtered_items) - (
                                    chunk_index + i + 1
                                )
                                eta_minutes = (
                                    remaining_items / items_per_second / 60
                                    if items_per_second > 0
                                    else 0
                                )

                                logger.info(
                                    f"Chunk: {chunk_progress:.1f}% - "
                                    f"Overall: {total_progress:.1f}% ({chunk_index + i + 1}/{len(filtered_items)}) - "
                                    f"Rate: {items_per_second:.2f} items/s - "
                                    f"ETA: {eta_minutes:.1f} minutes"
                                )

                        # Add this chunk's items to the collection
                        logger.info(
                            f"Adding {len(chunk_items)} items to vector database..."
                        )
                        chunk_add_start = time.time()

                        try:
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

            # Replace the original method with our patched version
            setattr(
                BitwigBrowserIndexer,
                "index_browser_content",
                index_browser_content_with_skip,
            )
            logger.info("✅ Patched indexer to skip existing devices")
        else:
            # Using default behavior (adds all devices without filtering)
            logger.info("✅ Using default indexer (will add all devices)")

        # Now proceed with indexing - reuse the controller we already verified
        if args.no_description:
            # Just build the base index without enhancement
            logger.info(
                "🔄 Building base device index (skipping description enhancement)..."
            )
            indexer = await build_index(
                persistent_dir=data_dir, existing_controller=controller
            )
            enhance_step_performed = False
        else:
            # Do the full process: build index + enhance
            logger.info("🔄 Building full device index with descriptions...")
            indexer = await build_and_enhance_index(
                persistent_dir=data_dir, existing_controller=controller
            )
            enhance_step_performed = True

        # Check if we have a valid indexer
        if indexer is None:
            logger.error(
                "❌ Indexing failed. Most common causes:\n"
                "1. Bitwig Studio is not running or not properly configured\n"
                "2. The OSC Controller extension is not enabled in Bitwig\n"
                "3. Ports 8000 and 9000 are in use by another application\n"
                "4. No project is open in Bitwig Studio\n\n"
                "Please check the logs above for more specific error messages."
            )
            return False

        # Display statistics if requested
        if not args.no_stats:
            display_index_stats(indexer)

        elapsed_time = time.time() - start_time
        logger.info("\n" + "=" * 80)
        logger.info(f"✅ Indexing completed in {elapsed_time:.1f} seconds")
        logger.info("=" * 80)

        # Suggest next steps
        logger.info("\n📌 Next Steps:")
        logger.info("1. Try searching the index:")
        logger.info(
            '   python dev_tools/manage_device_index.py search "warm analog synth"'
        )
        logger.info("\n2. Get device recommendations:")
        logger.info(
            '   python dev_tools/manage_device_index.py recommend "I need a distorted bass sound"'
        )

        logger.info("\n" + "=" * 80)
        return True

    except KeyboardInterrupt:
        logger.info("\n⚠️  Operation cancelled by user")
        return False

    except Exception as e:
        logger.exception(f"❌ Error during indexing: {e}")
        return False

    finally:
        # Make sure to stop the controller
        if "controller" in locals() and controller is not None:
            logger.info("Shutting down OSC controller...")
            controller.stop()


def get_data_dir(args):
    """Get the data directory from args or use default."""
    if hasattr(args, "data_dir") and args.data_dir:
        return args.data_dir
    else:
        # Use the default project data directory
        return os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data",
            "browser_index",
        )


def display_index_stats(indexer, as_json=False):
    """Display statistics about the device index."""
    # Get statistics
    device_count = indexer.get_device_count()
    if device_count == 0:
        logger.error("❌ No devices in the index. The index is empty.")
        return

    stats = indexer.get_collection_stats()

    if as_json:
        # Print as JSON
        print(json.dumps(stats, indent=2))
        return

    # Display in a nice formatted way
    logger.info("\n" + "=" * 80)
    logger.info("📊 INDEX STATISTICS")
    logger.info("=" * 80)

    logger.info(f"Total devices indexed: {stats['count']}")

    # Display description statistics if available
    if "with_description" in stats and "without_description" in stats:
        with_desc = stats["with_description"]
        without_desc = stats["without_description"]
        desc_percentage = stats.get("description_percentage", 0)
        logger.info("\nDescription Coverage:")
        logger.info(f"  - With descriptions: {with_desc} ({desc_percentage:.1f}%)")
        logger.info(f"  - Without descriptions: {without_desc}")

    if stats.get("categories"):
        logger.info(f"\nCategories ({len(stats['categories'])}):")
        for category in sorted(stats["categories"]):
            logger.info(f"  - {category}")

    if stats.get("types"):
        logger.info(f"\nTypes ({len(stats['types'])}):")
        for device_type in sorted(stats["types"]):
            logger.info(f"  - {device_type}")

    if stats.get("creators"):
        logger.info(f"\nCreators ({len(stats['creators'])}):")
        for creator in sorted(stats["creators"]):
            logger.info(f"  - {creator}")


def show_stats(args):
    """Show statistics about the device index."""
    data_dir = get_data_dir(args)

    try:
        # Initialize the indexer with the existing data
        indexer = BitwigBrowserIndexer(persistent_dir=data_dir)

        # Check if ChromaDB collection exists
        chroma_file = os.path.join(data_dir, "chroma.sqlite3")
        if not os.path.exists(chroma_file):
            logger.error(f"❌ ChromaDB database not found at {chroma_file}")
            logger.error("   Please create an index first:")
            logger.error("   python dev_tools/manage_device_index.py create")
            return False

        # Get collection info directly from ChromaDB since get_device_count() might be failing
        try:
            # We need to create a fresh ChromaDB client to avoid conflicts with existing instances
            import importlib
            import chromadb

            # Make sure we have a clean import
            importlib.reload(chromadb)

            # Import settings
            from chromadb.config import Settings

            # Create a client with anonymized_telemetry=False to match our indexer
            client = chromadb.PersistentClient(
                path=data_dir, settings=Settings(anonymized_telemetry=False)
            )

            # Get collections - handle API differences between ChromaDB versions
            try:
                collections = client.list_collections()
                # In newer versions (v0.6.0+), list_collections returns list of strings
                if collections and isinstance(collections[0], str):
                    collection_names = collections
                else:
                    # Older versions returned objects with a name attribute
                    collection_names = [c.name for c in collections]
            except Exception as e:
                logger.warning(f"⚠️  Error listing collections: {e}")
                # Try direct approach - if 'bitwig_devices' exists, this will work
                try:
                    client.get_collection(name="bitwig_devices")
                    collection_names = ["bitwig_devices"]
                except Exception:
                    collection_names = []

            if not collections or "bitwig_devices" not in collection_names:
                logger.error(
                    "❌ No 'bitwig_devices' collection found in the ChromaDB database"
                )
                logger.error("   Please create an index first:")
                logger.error("   python dev_tools/manage_device_index.py create")
                return False

            # Get the collection
            collection = client.get_collection(name="bitwig_devices")
            count = collection.count()

            if count == 0:
                logger.error("❌ The 'bitwig_devices' collection exists but is empty")
                logger.error("   Please create an index first:")
                logger.error("   python dev_tools/manage_device_index.py create")
                return False

            # Collection exists and has items, try using our indexer
            logger.info(f"✅ Found ChromaDB collection with {count} items")

            # Get stats using our built-in methods if possible
            try:
                # Display statistics
                display_index_stats(indexer, as_json=args.json)
                return True
            except Exception as stats_err:
                # If our methods fail, at least show the count from ChromaDB directly
                logger.warning(f"⚠️  Could not get detailed statistics: {stats_err}")
                if args.json:
                    print(
                        json.dumps(
                            {"count": count, "note": "Limited statistics available"}
                        )
                    )
                else:
                    logger.info("\n" + "=" * 80)
                    logger.info("📊 INDEX STATISTICS (LIMITED)")
                    logger.info("=" * 80)
                    logger.info(f"Total devices indexed: {count}")
                    logger.info(
                        "Note: Could not retrieve description coverage statistics"
                    )
                    logger.info("\n" + "=" * 80)
                return True

        except ImportError:
            logger.error(
                "❌ Could not import ChromaDB directly. Try reinstalling dependencies."
            )
            return False
        except Exception as inner_err:
            logger.error(f"❌ Error accessing ChromaDB directly: {inner_err}")
            return False

    except Exception as e:
        logger.error(f"❌ Error showing statistics: {e}")
        return False


def search_index(args):
    """Search the device index."""
    data_dir = get_data_dir(args)

    try:
        # Initialize the indexer
        indexer = BitwigBrowserIndexer(persistent_dir=data_dir)

        # Check if the index exists
        if indexer.get_device_count() == 0:
            logger.error(
                f"❌ No index found in {data_dir}. Please create an index first:"
            )
            logger.error("   python dev_tools/manage_device_index.py create")
            return False

        # Build filter options
        filter_options = {}
        if args.filter_category:
            filter_options["category"] = args.filter_category
        if args.filter_creator:
            filter_options["creator"] = args.filter_creator
        if args.filter_type:
            filter_options["type"] = args.filter_type

        # Use None if no filters were specified
        if not filter_options:
            filter_options = None

        # Perform search
        logger.info(f"🔍 Searching for: {args.query}")
        if filter_options:
            filters_text = ", ".join(f"{k}='{v}'" for k, v in filter_options.items())
            logger.info(f"   Filters: {filters_text}")

        results = indexer.search_devices(
            query=args.query, n_results=args.num_results, filter_options=filter_options
        )

        if not results:
            logger.warning(
                "⚠️  No results found. Try a different query or check your filters."
            )
            return False

        # Print results
        if args.json:
            # Output as JSON
            print(json.dumps(results, indent=2))
        else:
            # Pretty print results in text format
            print("\n" + "=" * 80)
            print(f"SEARCH RESULTS FOR: {args.query}")
            print("=" * 80)

            for i, result in enumerate(results):
                distance = result.get("distance", 0)
                similarity = 1 - distance if distance is not None else 0

                print(f"\n{i+1}. {result['name']}")
                print(f"   Type: {result.get('type', 'N/A')}")
                print(f"   Category: {result.get('category', 'N/A')}")
                print(f"   Creator: {result.get('creator', 'N/A')}")
                if result.get("tags"):
                    print(f"   Tags: {', '.join(result['tags'])}")
                if result.get("description"):
                    description = result["description"]
                    # Truncate long descriptions
                    if len(description) > 100:
                        description = description[:97] + "..."
                    print(f"   Description: {description}")
                print(f"   Similarity: {similarity:.2%}")

            print("\n" + "=" * 80)

        return True

    except Exception as e:
        logger.error(f"❌ Error searching index: {e}")
        return False


def recommend_devices(args):
    """Recommend devices based on a task description."""
    data_dir = get_data_dir(args)

    try:
        # Initialize the recommender
        recommender = BitwigDeviceRecommender(persistent_dir=data_dir)

        # Check if the index exists
        if recommender.indexer.get_device_count() == 0:
            logger.error(
                f"❌ No index found in {data_dir}. Please create an index first:"
            )
            logger.error("   python dev_tools/manage_device_index.py create")
            return False

        # Get recommendations
        logger.info(f"🔍 Getting device recommendations for: {args.description}")
        if args.filter_category or args.filter_type:
            filters = []
            if args.filter_category:
                filters.append(f"category='{args.filter_category}'")
            if args.filter_type:
                filters.append(f"type='{args.filter_type}'")
            logger.info(f"   Filters: {', '.join(filters)}")

        recommendations = recommender.recommend_devices(
            task_description=args.description,
            num_results=args.num_results,
            filter_category=args.filter_category,
            filter_type=args.filter_type,
        )

        if not recommendations:
            logger.warning(
                "⚠️  No recommendations found. Try a different description or check your filters."
            )
            return False

        # Print recommendations
        if args.json:
            # Output as JSON
            print(json.dumps(recommendations, indent=2))
        else:
            # Pretty print recommendations in text format
            print("\n" + "=" * 80)
            print(f"RECOMMENDED DEVICES FOR: {args.description}")
            print("=" * 80)

            for i, rec in enumerate(recommendations, 1):
                print(f"\n{i}. {rec['device']} ({rec['category']})")
                print(f"   Creator: {rec['creator']}")
                print(f"   Type: {rec['type']}")
                print(f"   Relevance: {rec['relevance_score']:.2f}")
                print(f"   Why: {rec['explanation']}")
                if rec.get("description"):
                    desc = rec["description"]
                    # Truncate long descriptions
                    if len(desc) > 100:
                        desc = desc[:97] + "..."
                    print(f"   Description: {desc}")

            print("\n" + "=" * 80)

        return True

    except Exception as e:
        logger.error(f"❌ Error getting recommendations: {e}")
        return False


async def enhance_index(args):
    """Enhance the device index with descriptions."""
    data_dir = get_data_dir(args)

    try:
        # Check if the index exists
        indexer = BitwigBrowserIndexer(persistent_dir=data_dir)
        if indexer.get_device_count() == 0:
            logger.error(
                f"❌ No index found in {data_dir}. Please create an index first:"
            )
            logger.error("   python dev_tools/manage_device_index.py create")
            return False

        # Enhance the index
        logger.info("🔄 Enhancing index with descriptions...")
        updated_count = await enhance_index_with_descriptions(persistent_dir=data_dir)

        if updated_count > 0:
            logger.info(
                f"✅ Successfully enhanced {updated_count} devices with descriptions"
            )
            return True
        else:
            logger.warning(
                "⚠️  No devices were enhanced. All devices may already have descriptions."
            )
            return False

    except Exception as e:
        logger.error(f"❌ Error enhancing index: {e}")
        return False


def clear_index(args):
    """Clear the device index.

    This removes the ChromaDB database file but preserves the directory structure.
    """
    data_dir = get_data_dir(args)

    try:
        # Check if index directory exists
        if not os.path.exists(data_dir):
            os.makedirs(data_dir, exist_ok=True)
            logger.info(f"✅ Created index directory at {data_dir}")
            return True  # Directory didn't exist but now it does

        # Check if any index exists
        chroma_db = os.path.join(data_dir, "chroma.sqlite3")
        if not os.path.exists(chroma_db):
            logger.info(f"ℹ️ No index found at {data_dir}, nothing to clear")
            return True  # No index to clear

        # Confirm deletion
        if not args.force:
            print("⚠️  This will delete the device index at:")
            print(f"   {data_dir}")
            print("Are you sure you want to continue? (yes/no): ", end="")
            response = input().strip().lower()
            if response != "yes":
                logger.info("❌ Operation cancelled")
                return False

        # Clear ChromaDB files
        try:
            os.remove(chroma_db)
            logger.info(f"✅ Removed device index: {chroma_db}")

            # Also remove any other ChromaDB files
            for extra_file in os.listdir(data_dir):
                if extra_file.startswith("chroma.") or extra_file.startswith("index."):
                    file_path = os.path.join(data_dir, extra_file)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                        logger.info(f"✅ Removed index file: {extra_file}")
        except Exception as e:
            logger.error(f"❌ Error removing database file: {e}")
            return False

        logger.info(
            "✅ Successfully cleared device index. Ready to create a new index."
        )
        return True

    except Exception as e:
        logger.error(f"❌ Error clearing index: {e}")
        return False


async def main():
    """Main function to process command line arguments."""
    # Create the main parser
    parser = argparse.ArgumentParser(
        description="Manage Bitwig Studio device index for search and recommendations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  ## Creating and Managing Indexes

  # Create a full device index (with descriptions - default):
  python dev_tools/manage_device_index.py create

  # Create index faster (without descriptions):
  python dev_tools/manage_device_index.py create --no-description

  # Update index but skip devices that already exist:
  python dev_tools/manage_device_index.py create --skip-existing

  # Fastest indexing (skip existing and no descriptions):
  python dev_tools/manage_device_index.py create --skip-existing --no-description

  # Clear the index:
  python dev_tools/manage_device_index.py clear

  # For a complete refresh, clear first then create a new index:
  python dev_tools/manage_device_index.py clear --force && python dev_tools/manage_device_index.py create

  ## Using the Index

  # Show index statistics:
  python dev_tools/manage_device_index.py stats

  # Search for devices by description:
  python dev_tools/manage_device_index.py search "warm analog synth"

  # Get device recommendations for a specific task:
  python dev_tools/manage_device_index.py recommend "I need a distorted bass sound"

  # Search with filters:
  python dev_tools/manage_device_index.py search "reverb" --filter-category "Effects"

  ## New Features

  # The indexer now automatically creates different track contexts (audio, instrument)
  # to better access all browser tabs and device types. This creates a more complete
  # device index with better metadata about categories and types.
""",
    )

    # Add common options for all subcommands
    parser.add_argument(
        "--data-dir",
        help="Custom directory for the index (default: project's data/browser_index)",
    )

    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # 'create' command
    create_parser = subparsers.add_parser(
        "create", help="Create or update the device index"
    )
    create_parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip existing entries (don't update them if they already exist)",
    )
    create_parser.add_argument(
        "--no-description",
        action="store_true",
        help="Skip enhancing devices with descriptions (faster, for testing/debugging)",
    )
    create_parser.add_argument(
        "--no-stats",
        action="store_true",
        help="Don't display statistics after indexing",
    )

    # 'stats' command
    stats_parser = subparsers.add_parser(
        "stats", help="Show statistics about the device index"
    )
    stats_parser.add_argument(
        "--json",
        action="store_true",
        help="Output statistics as JSON",
    )

    # 'search' command
    search_parser = subparsers.add_parser(
        "search", help="Search for devices in the index"
    )
    search_parser.add_argument(
        "query",
        help="Search query (e.g., 'warm analog synth')",
    )
    search_parser.add_argument(
        "--num-results",
        type=int,
        default=5,
        help="Number of results to return (default: 5)",
    )
    search_parser.add_argument(
        "--filter-category",
        help="Filter results by category (e.g., 'Effects')",
    )
    search_parser.add_argument(
        "--filter-creator",
        help="Filter results by creator (e.g., 'Bitwig')",
    )
    search_parser.add_argument(
        "--filter-type",
        help="Filter results by type (e.g., 'Synthesizer')",
    )
    search_parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )

    # 'recommend' command
    recommend_parser = subparsers.add_parser(
        "recommend", help="Get device recommendations for a task"
    )
    recommend_parser.add_argument(
        "description",
        help="Natural language description of your audio task",
    )
    recommend_parser.add_argument(
        "--num-results",
        type=int,
        default=5,
        help="Number of recommendations to return (default: 5)",
    )
    recommend_parser.add_argument(
        "--filter-category",
        help="Filter recommendations by category (e.g., 'Effects')",
    )
    recommend_parser.add_argument(
        "--filter-type",
        help="Filter recommendations by type (e.g., 'Synthesizer')",
    )
    recommend_parser.add_argument(
        "--json",
        action="store_true",
        help="Output recommendations as JSON",
    )

    # Note: 'enhance' command removed since enhancing is now the default in 'create'

    # 'clear' command
    clear_parser = subparsers.add_parser(
        "clear", help="Clear the device index completely (without rebuilding)"
    )
    clear_parser.add_argument(
        "--force",
        action="store_true",
        help="Clear without confirmation prompt",
    )

    # Parse arguments
    args = parser.parse_args()

    # If no command provided, show help
    if not args.command:
        parser.print_help()
        return

    # Handle commands
    try:
        if args.command == "create":
            await create_full_index(args)
        elif args.command == "stats":
            show_stats(args)
        elif args.command == "search":
            search_index(args)
        elif args.command == "recommend":
            recommend_devices(args)
        elif args.command == "clear":
            clear_index(args)
        else:
            parser.print_help()

    except KeyboardInterrupt:
        logger.info("\n⚠️  Operation cancelled by user")

    except Exception as e:
        logger.exception(f"Unhandled error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
