#!/usr/bin/env python
"""
Device Recommendation CLI

Command-line interface for recommending Bitwig devices based on natural language task descriptions.
"""

import argparse
import json
import logging
import sys

from bitwig_mcp_server.utils.device_recommender import BitwigDeviceRecommender

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)


def recommend_devices(
    task_description: str,
    persistent_dir: str = None,
    num_results: int = 5,
    filter_category: str = None,
    filter_type: str = None,
    format_output: str = "text",
) -> None:
    """Recommend devices based on a task description.

    Args:
        task_description: Natural language description of the audio task
        persistent_dir: Directory where the ChromaDB data is stored
        num_results: Number of results to return
        filter_category: Optional category filter
        filter_type: Optional type filter
        format_output: Output format (text, json)
    """
    try:
        # Initialize the recommender
        recommender = BitwigDeviceRecommender(persistent_dir=persistent_dir)

        # Check if we have any devices in the index
        if recommender.indexer.get_device_count() == 0:
            if format_output == "json":
                print(
                    json.dumps(
                        {
                            "error": "No devices in index",
                            "message": "The device index is empty. Please run the indexer first.",
                            "command": "python -m bitwig_mcp_server.utils.index_browser index",
                        },
                        indent=2,
                    )
                )
            else:
                print("\n⚠️  ERROR: Device index is empty")
                print("   The device index doesn't contain any devices.")
                print("   Please run the indexer first:")
                print("   python -m bitwig_mcp_server.utils.index_browser index")
                print(
                    "\n   Make sure Bitwig Studio is running when you run the indexer.\n"
                )
            return

        # Get recommendations
        recommendations = recommender.recommend_devices(
            task_description=task_description,
            num_results=num_results,
            filter_category=filter_category,
            filter_type=filter_type,
        )

        # Check if we got any recommendations
        if not recommendations:
            if format_output == "json":
                print(
                    json.dumps(
                        {
                            "error": "No recommendations found",
                            "message": "No devices were found matching your criteria.",
                        },
                        indent=2,
                    )
                )
            else:
                print("\n⚠️  No devices found matching your criteria")
                print("   Try a different search or check your filters.")
                print("   You can see available filters with: --list-filters\n")
            return

        # Format and print results
        if format_output == "json":
            print(json.dumps(recommendations, indent=2))
        else:
            # Text format
            print("\n=== Recommended Devices ===\n")
            for i, rec in enumerate(recommendations, 1):
                print(f"{i}. {rec['device']} ({rec['category']})")
                print(f"   Creator: {rec['creator']}")
                print(f"   Relevance: {rec['relevance_score']:.2f}")
                print(f"   Why: {rec['explanation']}")
                if rec.get("description"):
                    desc = rec["description"]
                    print(
                        f"   Description: {desc[:100]}{('...' if len(desc) > 100 else '')}"
                    )
                print()

    except Exception as e:
        logger.exception(f"Error recommending devices: {e}")
        if format_output == "json":
            print(
                json.dumps(
                    {
                        "error": str(e),
                        "message": "An error occurred while getting recommendations.",
                    },
                    indent=2,
                )
            )
        else:
            print(f"\n⚠️  ERROR: {str(e)}")
            print("   An error occurred while getting recommendations.")
            print(
                "   Please check that your vector database is properly initialized.\n"
            )


def main():
    """Main function to handle command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Bitwig Device Recommender",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Get device recommendations:
  python -m bitwig_mcp_server.utils.recommend_devices "I want to add some subtle distortion to my bass"

  # Get recommendations with filters:
  python -m bitwig_mcp_server.utils.recommend_devices "bass compression" --filter-category "Effects"

  # List available filter values:
  python -m bitwig_mcp_server.utils.recommend_devices --list-filters

  # Get recommendations in JSON format:
  python -m bitwig_mcp_server.utils.recommend_devices "warm analog pad" --format json
""",
    )

    # Main arguments (keep it simple - this is more intuitive for users)
    parser.add_argument(
        "task", nargs="?", help="Natural language description of your audio task"
    )

    parser.add_argument(
        "--persistent-dir",
        default=None,
        help="Directory where the vector database is stored (default: project's data/browser_index)",
    )

    parser.add_argument(
        "--num-results",
        type=int,
        default=5,
        help="Number of results to return (default: 5)",
    )

    parser.add_argument("--filter-category", help="Filter results by category")

    parser.add_argument("--filter-type", help="Filter results by type")

    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )

    parser.add_argument(
        "--list-filters", action="store_true", help="List available filter options"
    )

    # Parse arguments
    args = parser.parse_args()

    try:
        # Handle commands
        if args.list_filters:
            # Initialize the recommender for filter listing
            recommender = BitwigDeviceRecommender(persistent_dir=args.persistent_dir)
            format_output = args.format

            try:
                filters = recommender.get_available_filters()

                if format_output == "json":
                    print(json.dumps(filters, indent=2))
                else:
                    print("\n=== Available Filters ===\n")

                    if (
                        not filters.get("categories")
                        and not filters.get("types")
                        and not filters.get("creators")
                    ):
                        print("⚠️  No filters found. The index may be empty.")
                        print("   Please run the indexer first:")
                        print(
                            "   python -m bitwig_mcp_server.utils.index_browser index"
                        )
                        return

                    print("Categories:")
                    for category in filters.get("categories", []):
                        print(f"  - {category}")
                    print("\nTypes:")
                    for type_ in filters.get("types", []):
                        print(f"  - {type_}")
                    print("\nCreators:")
                    for creator in filters.get("creators", []):
                        print(f"  - {creator}")

            except Exception as e:
                logger.exception(f"Error listing filters: {e}")
                if format_output == "json":
                    print(
                        json.dumps(
                            {
                                "error": str(e),
                                "message": "An error occurred while listing filters.",
                            },
                            indent=2,
                        )
                    )
                else:
                    print(f"\n⚠️  ERROR: {str(e)}")
                    print("   An error occurred while listing filters.\n")

        elif args.task:
            # Call the search function with the task
            recommend_devices(
                task_description=args.task,
                persistent_dir=args.persistent_dir,
                num_results=args.num_results,
                filter_category=args.filter_category,
                filter_type=args.filter_type,
                format_output=args.format,
            )

        else:
            # If no task or list-filters flag, show help
            parser.print_help()

    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        return

    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        print(f"\n⚠️  ERROR: {str(e)}")
        print("   An unexpected error occurred.\n")


if __name__ == "__main__":
    main()
