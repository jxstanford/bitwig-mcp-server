#!/usr/bin/env python
"""
Browser Indexing Script

This script is a command-line utility to index the Bitwig Studio browser content
and perform searches against the index.

Usage:
    python -m bitwig_mcp_server.utils.index_browser index
    python -m bitwig_mcp_server.utils.index_browser search "warm analog bass synth"
    python -m bitwig_mcp_server.utils.index_browser stats
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import traceback

from bitwig_mcp_server.utils.browser_indexer import BitwigBrowserIndexer, build_index


# Use a more colorful and detailed logging format
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

# Set up the logger for this module
logger = logging.getLogger(__name__)

# Default data directory
DEFAULT_DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "browser_index"
)


async def perform_search(
    query: str,
    persistent_dir: str = None,
    num_results: int = 5,
    filter_category: str = None,
    filter_creator: str = None,
    filter_type: str = None,
):
    """Search the device index.

    Args:
        query: Search query
        persistent_dir: Directory where the ChromaDB data is stored
        num_results: Number of results to return
        filter_category: Optional category filter
        filter_creator: Optional creator filter
        filter_type: Optional type filter

    Returns:
        List of search results
    """
    # Initialize the indexer with the existing data
    indexer = BitwigBrowserIndexer(persistent_dir=persistent_dir)

    # Check if the index exists
    if indexer.get_device_count() == 0:
        logger.error(
            f"No index found in {persistent_dir}. Please run index_browser.py --index first."
        )
        return []

    # Build filter options
    filter_options = {}
    if filter_category:
        filter_options["category"] = filter_category
    if filter_creator:
        filter_options["creator"] = filter_creator
    if filter_type:
        filter_options["type"] = filter_type

    # Use None if no filters were specified
    if not filter_options:
        filter_options = None

    # Perform search
    results = indexer.search_devices(
        query, n_results=num_results, filter_options=filter_options
    )

    return results


async def main():
    """Main function to handle command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Bitwig Browser Indexer and Search Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Build the index (with Bitwig Studio running):
  python -m bitwig_mcp_server.utils.index_browser index

  # Search for devices:
  python -m bitwig_mcp_server.utils.index_browser search "warm analog synth"

  # Search with filters:
  python -m bitwig_mcp_server.utils.index_browser search "reverb" --filter-category "Effects" --num-results 10

  # Show statistics about the index:
  python -m bitwig_mcp_server.utils.index_browser stats
""",
    )

    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Index command
    index_parser = subparsers.add_parser("index", help="Index the browser content")
    index_parser.add_argument(
        "--persistent-dir",
        default=DEFAULT_DATA_DIR,
        help=f"Directory to store the vector database (default: {DEFAULT_DATA_DIR})",
    )
    index_parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear existing index before rebuilding (warning: this will delete all existing data)",
    )

    # Search command
    search_parser = subparsers.add_parser("search", help="Search the device index")
    search_parser.add_argument(
        "query", help="Search query (e.g., 'warm analog bass synth')"
    )
    search_parser.add_argument(
        "--persistent-dir",
        default=DEFAULT_DATA_DIR,
        help=f"Directory where the vector database is stored (default: {DEFAULT_DATA_DIR})",
    )
    search_parser.add_argument(
        "--num-results",
        type=int,
        default=5,
        help="Number of results to return (default: 5)",
    )
    search_parser.add_argument(
        "--filter-category",
        help="Filter results by category (e.g., 'Effects', 'Instruments')",
    )
    search_parser.add_argument(
        "--filter-creator", help="Filter results by creator (e.g., 'Bitwig')"
    )
    search_parser.add_argument(
        "--filter-type",
        help="Filter results by type (e.g., 'Synthesizer', 'Modulator')",
    )
    search_parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="text",
        help="Output format (json or text, default: text)",
    )

    # Stats command
    stats_parser = subparsers.add_parser(
        "stats", help="Show statistics about the index"
    )
    stats_parser.add_argument(
        "--persistent-dir",
        default=DEFAULT_DATA_DIR,
        help=f"Directory where the vector database is stored (default: {DEFAULT_DATA_DIR})",
    )
    stats_parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="text",
        help="Output format (json or text, default: text)",
    )

    # Parse arguments
    args = parser.parse_args()

    # If no command provided, show help
    if not args.command:
        parser.print_help()
        return

    try:
        # Handle commands
        if args.command == "index":
            # Check if Bitwig is running (this is just a warning, will try anyway)
            logger.info("=" * 80)
            logger.info("Starting Bitwig browser indexing")
            logger.info("=" * 80)
            logger.info(
                "IMPORTANT: Bitwig Studio should be running with a project open"
            )
            logger.info(f"Index will be stored at: {args.persistent_dir}")

            # If clear flag is set, try to remove the database
            if args.clear and os.path.exists(args.persistent_dir):
                logger.warning(f"Clearing existing index at {args.persistent_dir}")
                # Don't delete the directory itself, just the contents
                chroma_dir = os.path.join(args.persistent_dir, "chroma")
                if os.path.exists(chroma_dir):
                    import shutil

                    shutil.rmtree(chroma_dir)
                    logger.info("Existing index cleared successfully")

            # Build the index
            indexer = await build_index(persistent_dir=args.persistent_dir)
            if indexer:
                logger.info("=" * 80)
                logger.info("Indexing completed successfully!")
                logger.info(f"Devices indexed: {indexer.get_device_count()}")
                logger.info("=" * 80)
            else:
                logger.error("Indexing failed. Please check the logs for details.")

        elif args.command == "search":
            logger.info(f"Searching for: {args.query}")
            if args.filter_category or args.filter_creator or args.filter_type:
                filters = []
                if args.filter_category:
                    filters.append(f"category='{args.filter_category}'")
                if args.filter_creator:
                    filters.append(f"creator='{args.filter_creator}'")
                if args.filter_type:
                    filters.append(f"type='{args.filter_type}'")
                logger.info(f"Filters: {', '.join(filters)}")

            results = await perform_search(
                query=args.query,
                persistent_dir=args.persistent_dir,
                num_results=args.num_results,
                filter_category=args.filter_category,
                filter_creator=args.filter_creator,
                filter_type=args.filter_type,
            )

            if not results:
                logger.warning(
                    "No results found. Try a different query or check if the index exists."
                )
                return

            # Print results
            if args.format == "json":
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
                        print(f"   Description: {result['description']}")
                    print(f"   Similarity: {similarity:.2%}")

                print("\n" + "=" * 80)

        elif args.command == "stats":
            # Initialize the indexer with the existing data
            try:
                indexer = BitwigBrowserIndexer(persistent_dir=args.persistent_dir)

                # Get stats
                stats = indexer.get_collection_stats()

                if args.format == "json":
                    print(json.dumps(stats, indent=2))
                else:
                    # Pretty print stats in text format
                    print("\n" + "=" * 80)
                    print("DEVICE INDEX STATISTICS")
                    print("=" * 80)

                    print(f"\nTotal devices indexed: {stats['count']}")

                    print(f"\nCategories ({len(stats['categories'])}):")
                    for category in stats["categories"]:
                        print(f"  - {category}")

                    print(f"\nTypes ({len(stats['types'])}):")
                    for device_type in stats["types"]:
                        print(f"  - {device_type}")

                    print(f"\nCreators ({len(stats['creators'])}):")
                    for creator in stats["creators"]:
                        print(f"  - {creator}")

                    print("\n" + "=" * 80)

            except Exception as e:
                logger.error(f"Error getting statistics: {e}")
                logger.error(f"Index directory: {args.persistent_dir}")
                logger.error(
                    "The index may not exist or may be corrupted. Try building it first."
                )

        else:
            parser.print_help()

    except KeyboardInterrupt:
        logger.info("\nOperation cancelled by user")
        return

    except Exception as e:
        logger.error(f"Error during execution: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
