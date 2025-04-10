#!/usr/bin/env python3
"""
Utility for filtering entities in the Bitwig browser based on filter categories
and searching by name.

This tool helps investigate how metadata is stored in the browser and how
to extract it properly via OSC.
"""

import asyncio
import argparse
import logging
import sys
from typing import Dict, List, Optional, Tuple, Any

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("filter_browser_entities")

# Add parent directory to path so we can import our modules
sys.path.append("..")

from bitwig_mcp_server.osc.controller import BitwigOSCController
from bitwig_mcp_server.settings import Settings


async def verify_bitwig_connection() -> Tuple[bool, Optional[BitwigOSCController]]:
    """Verify that Bitwig is running and responding to OSC messages."""
    settings = Settings()
    controller = BitwigOSCController(
        ip=settings.bitwig_host,
        send_port=settings.bitwig_send_port,
        receive_port=settings.bitwig_receive_port,
    )

    try:
        # Start the controller
        controller.start()

        # Wait for connection
        await asyncio.sleep(2.0)

        # Try to get basic data from Bitwig
        controller.client.refresh()
        await asyncio.sleep(1.0)

        # Check if we're receiving data
        tempo = controller.server.get_message("/tempo/raw")
        project_name = controller.server.get_message("/project/name")

        if tempo is None and project_name is None:
            logger.error("❌ Could not connect to Bitwig Studio")
            logger.error(
                "Please make sure Bitwig Studio is running with a project open"
            )
            logger.error("and the OSC Controller extension is enabled")
            controller.stop()
            return False, None

        logger.info(
            f"✅ Successfully connected to Bitwig Studio (project: {project_name})"
        )
        return True, controller
    except Exception as e:
        logger.error(f"❌ Failed to connect to Bitwig Studio: {e}")
        if controller:
            try:
                controller.stop()
            except Exception:
                pass
        return False, None


async def open_browser(controller: BitwigOSCController) -> bool:
    """Open the Bitwig browser with retry logic.

    Args:
        controller: The BitwigOSCController instance

    Returns:
        bool: True if browser was successfully opened, False otherwise
    """
    # Try multiple times to open the browser
    for attempt in range(3):  # Try up to 3 times
        logger.info(f"Opening Bitwig browser (attempt {attempt+1}/3)...")

        # Make sure client is refreshed
        controller.client.refresh()
        await asyncio.sleep(1.0)

        # Try to open browser
        controller.client.browse_for_device("after")
        await asyncio.sleep(2.0)  # Longer wait time for browser to open

        # Check if browser is active
        browser_active = controller.server.get_message("/browser/isActive")
        logger.info(f"Browser active: {browser_active}")

        if browser_active == "1" or browser_active == 1:
            logger.info("✅ Browser successfully opened")
            return True

        if attempt < 2:  # Don't do cleanup on last attempt
            logger.warning(
                f"Browser failed to open on attempt {attempt+1}, retrying..."
            )
            # Try closing browser if it might be stuck
            controller.client.cancel_browser()
            await asyncio.sleep(1.0)

    logger.error(
        "❌ Browser failed to open after multiple attempts. Please check if:"
        "\n1. Bitwig Studio is running with a project open"
        "\n2. The OSC Controller extension is enabled in Bitwig"
        "\n3. Bitwig is not in fullscreen mode (try switching to window mode)"
    )
    return False


async def get_browser_tabs(controller: BitwigOSCController) -> List[str]:
    """Get the list of available tabs in the Bitwig browser using direct OSC queries.

    This attempts to get tabs directly by using individual tab addresses.
    """
    # Navigate to first tab for consistency
    logger.info("Navigating to first browser tab...")
    for _ in range(10):  # Try up to 10 times
        controller.client.send("/browser/tab/navigate", "-")
        await asyncio.sleep(0.3)

    # Now try to get tab names directly
    tab_names = []
    max_tabs = 15  # Maximum number of tabs to check

    logger.info("Trying to get tab names directly...")
    for tab_index in range(max_tabs):
        # Try to get each tab by index
        controller.client.send(f"/browser/tab/name/{tab_index}", 1)
        await asyncio.sleep(0.5)

        tab_name = controller.server.get_message(f"/browser/tab/name/{tab_index}")
        if tab_name:
            logger.info(f"Found tab {tab_index}: {tab_name}")
            tab_names.append(tab_name)
        else:
            # Try alternative - direct client.send_and_wait
            try:
                controller.client.send(f"/browser/tab/{tab_index}", 1)
                await asyncio.sleep(0.5)
                tab_info = controller.server.get_message(f"/browser/tab/{tab_index}")
                if tab_info:
                    logger.info(f"Found tab {tab_index} via direct query: {tab_info}")
                    tab_names.append(tab_info)
                    continue
            except Exception:
                pass

            # If we're at index 0 and still didn't get a tab, fallback to defaults
            if tab_index == 0 and not tab_names:
                logger.warning("Could not get tab names directly, using defaults")
                default_tabs = [
                    "Devices",
                    "Presets",
                    "Samples",
                    "Multisamples",
                    "Clips",
                    "MIDI Files",
                    "Projects",
                    "Packages",
                ]
                logger.info(f"Using default tabs list: {default_tabs}")
                return default_tabs

            # If we can't get this tab, assume we've reached the end
            break

    # If we got tab names, return them
    if tab_names:
        logger.info(f"Successfully retrieved {len(tab_names)} tabs directly")
        return tab_names
    else:
        # Fallback to defaults if we couldn't get any tabs
        default_tabs = [
            "Devices",
            "Presets",
            "Samples",
            "Multisamples",
            "Clips",
            "MIDI Files",
            "Projects",
            "Packages",
        ]
        logger.info(f"Using default tabs list: {default_tabs}")
        return default_tabs


async def navigate_to_tab(
    controller: BitwigOSCController, tab_index: int, tab_names: List[str]
) -> bool:
    """Navigate to a specific browser tab.

    Args:
        controller: The BitwigOSCController instance
        tab_index: The index of the tab to navigate to
        tab_names: List of tab names

    Returns:
        bool: True if navigation was successful, False otherwise
    """
    if tab_index >= len(tab_names):
        logger.error(
            f"Tab index {tab_index} is out of range. Available tabs: {len(tab_names)}"
        )
        return False

    target_tab = tab_names[tab_index]
    logger.info(f"Navigating to tab: {target_tab} (index {tab_index})")

    # First, go to the first tab
    for _ in range(10):  # Try up to 10 times
        controller.client.send("/browser/tab/navigate", "-")
        await asyncio.sleep(0.3)

    # Then navigate forward to the target tab
    for _ in range(tab_index):
        controller.client.send("/browser/tab/navigate", "+")
        await asyncio.sleep(0.5)

    # Verify we're on the right tab
    await asyncio.sleep(1.0)
    current_tab = controller.server.get_message("/browser/tab")

    if current_tab != target_tab:
        logger.error(
            f"Failed to navigate to tab {target_tab}. Current tab: {current_tab}"
        )
        return False

    logger.info(f"Successfully navigated to tab: {current_tab}")
    return True


async def get_filter_columns(controller: BitwigOSCController) -> List[Dict[str, Any]]:
    """Get filter columns for the current browser tab."""
    # Get the number of filter columns
    columns = []
    column_index = 0

    while True:
        # Check if this filter column exists
        try:
            # Send a request for the filter name
            controller.client.send(f"/browser/filter/{column_index}/name", 1)
            await asyncio.sleep(0.3)

            # Check if we got a response
            column_name = controller.server.get_message(
                f"/browser/filter/{column_index}/name"
            )

            if not column_name:
                # Try one more time with a longer wait
                await asyncio.sleep(0.5)
                column_name = controller.server.get_message(
                    f"/browser/filter/{column_index}/name"
                )
                if not column_name:
                    break

            column_info = {"index": column_index, "name": column_name, "entries": []}

            # Get filter entries
            entry_index = 0
            while True:
                try:
                    # Send a request for the filter item
                    controller.client.send(
                        f"/browser/filter/{column_index}/item/{entry_index}", 1
                    )
                    await asyncio.sleep(0.2)

                    # Check if we got a response
                    entry_name = controller.server.get_message(
                        f"/browser/filter/{column_index}/item/{entry_index}"
                    )

                    if not entry_name:
                        break

                    # Get selection state
                    controller.client.send(
                        f"/browser/filter/{column_index}/item/{entry_index}/selected", 1
                    )
                    await asyncio.sleep(0.2)
                    is_selected = controller.server.get_message(
                        f"/browser/filter/{column_index}/item/{entry_index}/selected"
                    )

                    column_info["entries"].append(
                        {
                            "index": entry_index,
                            "name": entry_name,
                            "selected": is_selected == "1" or is_selected == 1,
                        }
                    )
                    entry_index += 1

                except Exception as e:
                    logger.debug(f"Error getting filter entry {entry_index}: {e}")
                    break

            columns.append(column_info)
            column_index += 1

        except Exception as e:
            logger.debug(f"Error getting filter column {column_index}: {e}")
            break

    return columns


async def apply_filter(
    controller: BitwigOSCController,
    filter_selections: Dict[str, str],
    columns: List[Dict[str, Any]],
) -> bool:
    """Apply filters to the browser based on column name and value pairs."""
    for column_name, value_name in filter_selections.items():
        # Find the column index
        column_index = None
        column_info = None
        for col in columns:
            if col["name"] == column_name:
                column_index = col["index"]
                column_info = col
                break

        if column_index is None:
            logger.warning(f"Column '{column_name}' not found")
            continue

        # Find the value index
        value_index = None
        for entry in column_info["entries"]:
            if entry["name"] == value_name:
                value_index = entry["index"]
                break

        if value_index is None:
            logger.warning(f"Value '{value_name}' not found in column '{column_name}'")
            continue

        # Apply the filter
        logger.info(f"Selecting {value_name} in {column_name}")
        controller.client.send(
            f"/browser/filter/{column_index}/select/{value_index}", 1
        )
        await asyncio.sleep(0.5)  # Give Bitwig time to apply the filter

    # Briefly wait for all filters to apply
    await asyncio.sleep(1.0)
    return True


async def search_by_name(controller: BitwigOSCController, name: str) -> None:
    """Set the search field in the browser to search by name."""
    logger.info(f"Searching for: {name}")
    controller.client.send("/browser/search", name)

    # Briefly wait for search to apply
    await asyncio.sleep(1.5)


async def get_results(
    controller: BitwigOSCController, max_items: int = 10
) -> List[Dict[str, Any]]:
    """Get the current results in the browser after applying filters."""
    results = []

    # Wait a moment for results to populate fully
    await asyncio.sleep(1.0)

    for i in range(max_items):
        # Check if this result exists
        controller.client.send(f"/browser/result/{i}", 1)
        await asyncio.sleep(0.2)

        # Check if we got a response
        name = controller.server.get_message(f"/browser/result/{i}")
        if not name:
            break

        result = {"index": i, "name": name, "metadata": {}}

        # Try to get metadata - there are multiple approaches we can try

        # 1. Direct properties
        properties = [
            "type",
            "category",
            "creator",
            "tags",
            "path",
            "location",
            "description",
        ]

        for prop in properties:
            controller.client.send(f"/browser/result/{i}/{prop}", 1)
            await asyncio.sleep(0.2)
            value = controller.server.get_message(f"/browser/result/{i}/{prop}")
            if value:
                result["metadata"][prop] = value

        # If a specific search term is being looked for, log more details
        if name and "Stereo Split" in name:
            logger.info(f"Found match for 'Stereo Split' at index {i}: {name}")

            # Get additional details
            for prop in ["column", "property", "field", "value", "data"]:
                for j in range(5):  # Try up to 5 indices
                    controller.client.send(f"/browser/result/{i}/{prop}/{j}", 1)
                    await asyncio.sleep(0.2)
                    prop_value = controller.server.get_message(
                        f"/browser/result/{i}/{prop}/{j}"
                    )
                    if prop_value:
                        result["metadata"][f"{prop}_{j}"] = prop_value

        results.append(result)

    return results


async def run_filter_search(args: argparse.Namespace) -> None:
    """Main function to run the filter and search operations."""
    # Connect to Bitwig
    success, controller = await verify_bitwig_connection()
    if not success or controller is None:
        return

    try:
        # Open the browser
        if not await open_browser(controller):
            logger.error("Cannot proceed without browser access")
            return

        # Get browser tabs
        tabs = await get_browser_tabs(controller)
        logger.info(f"Available browser tabs: {tabs}")

        if args.tab >= len(tabs):
            logger.error(
                f"Tab index {args.tab} is out of range. Available tabs: {len(tabs)}"
            )
            return

        # Navigate to the specified tab
        if not await navigate_to_tab(controller, args.tab, tabs):
            logger.error(f"Failed to navigate to tab {args.tab}")
            return

        # Get filter columns for the selected tab
        columns = await get_filter_columns(controller)
        logger.info("Available filter columns:")
        for col in columns:
            logger.info(f"  {col['name']}: {[e['name'] for e in col['entries']]}")

        # Apply filters if specified
        if args.filters:
            filter_dict = {}
            for filter_str in args.filters:
                try:
                    column, value = filter_str.split(":", 1)
                    filter_dict[column] = value
                except ValueError:
                    logger.error(
                        f"Invalid filter format: {filter_str}. Use 'column:value'"
                    )

            if filter_dict:
                logger.info(f"Applying filters: {filter_dict}")
                await apply_filter(controller, filter_dict, columns)

        # Apply search if specified
        if args.search:
            await search_by_name(controller, args.search)

        # Get and display results
        results = await get_results(controller, args.max_results)

        logger.info(f"Found {len(results)} results:")
        for i, result in enumerate(results):
            logger.info(f"\nResult {i+1}: {result['name']}")
            logger.info("Metadata:")
            for key, value in result["metadata"].items():
                logger.info(f"  {key}: {value}")

        # Output detailed information for the first result
        if results:
            logger.info("\nDetailed examination of first result:")
            # Skip first result assignment as it's not used
            # first_result = results[0]

            # OSC browser attributes investigation
            attributes = [
                "name",
                "type",
                "category",
                "creator",
                "tags",
                "path",
                "location",
                "description",
                "selected",
            ]

            for attr in attributes:
                controller.client.send(f"/browser/result/0/{attr}", 1)
                await asyncio.sleep(0.2)
                value = controller.server.get_message(f"/browser/result/0/{attr}")
                if value:
                    logger.info(f"  /browser/result/0/{attr}: {value}")

            # Try to get properties that might be nested
            for prop in ["property", "column", "field", "value", "data"]:
                for index in range(5):  # Try a few indices
                    controller.client.send(f"/browser/result/0/{prop}/{index}", 1)
                    await asyncio.sleep(0.2)
                    value = controller.server.get_message(
                        f"/browser/result/0/{prop}/{index}"
                    )
                    if value:
                        logger.info(f"  /browser/result/0/{prop}/{index}: {value}")

    finally:
        # Close browser
        controller.client.cancel_browser()
        await asyncio.sleep(0.5)

        # Clean up
        if controller:
            controller.stop()


def main():
    """Parse command line arguments and run the tool."""
    parser = argparse.ArgumentParser(
        description="Filter and search entities in the Bitwig browser"
    )

    parser.add_argument(
        "--tab", type=int, default=0, help="Browser tab index to use (default: 0)"
    )

    parser.add_argument(
        "--filters",
        nargs="+",
        help="Filters to apply in format 'column:value' (e.g. 'Category:Instrument')",
    )

    parser.add_argument("--search", type=str, help="Text to search for in the browser")

    parser.add_argument(
        "--max-results",
        type=int,
        default=10,
        help="Maximum number of results to display (default: 10)",
    )

    args = parser.parse_args()

    # Run the async function
    asyncio.run(run_filter_search(args))


if __name__ == "__main__":
    main()
