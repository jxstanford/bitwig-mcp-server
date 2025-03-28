#!/usr/bin/env python
"""
Debug tools for Bitwig browser and OSC communication.

This module contains utilities for debugging Bitwig Studio OSC communication
and browser functionality.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple

from bitwig_mcp_server.osc.controller import BitwigOSCController

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def check_connection() -> bool:
    """Test connection to Bitwig Studio and verify OSC communication.

    Returns:
        bool: True if connection is successful, False otherwise
    """
    controller = None
    try:
        logger.info("Initializing OSC controller...")
        controller = BitwigOSCController()

        # Start the controller
        controller.start()
        await asyncio.sleep(1.0)

        # Try to get a basic response from Bitwig
        logger.info("Attempting to communicate with Bitwig Studio...")

        # Send a refresh command
        controller.client.refresh()
        await asyncio.sleep(1)

        # Try to get current tempo
        tempo = controller.server.get_message("/transport/tempo")
        logger.info(f"Project tempo: {tempo}")

        if tempo is not None:
            logger.info("✅ Successfully connected to Bitwig Studio")
            return True
        else:
            logger.error("❌ Connected but not receiving data from Bitwig Studio")
            logger.error("Please ensure Bitwig Studio is running with a project open")
            logger.error("and that OSC is enabled in Bitwig settings.")
            return False

    except Exception as e:
        logger.error(f"❌ Error connecting to Bitwig Studio: {e}")
        return False
    finally:
        # Cleanup
        if controller is not None:
            controller.stop()
            logger.info("Controller stopped")


async def inspect_filters(controller: BitwigOSCController) -> Dict[int, Dict]:
    """Perform detailed inspection of browser filters.

    Args:
        controller: BitwigOSCController instance connected to Bitwig

    Returns:
        Dict: Dictionary of filter information with items and selection status
    """
    logger.info("\nDetailed filter inspection:")
    browser_filters = {}

    for filter_idx in range(1, 7):
        filter_exists = controller.server.get_message(
            f"/browser/filter/{filter_idx}/exists"
        )

        if filter_exists:
            filter_name = controller.server.get_message(
                f"/browser/filter/{filter_idx}/name"
            )
            logger.info(f"\nFilter {filter_idx}: {filter_name}")

            # Store filter info
            filter_info = {
                "name": filter_name,
                "items": {},
                "selected_item": None,
            }

            # Examine all items in this filter
            logger.info("  Items:")
            selected_item = None

            for item_idx in range(1, 17):  # Check up to 16 items per filter
                item_exists = controller.server.get_message(
                    f"/browser/filter/{filter_idx}/item/{item_idx}/exists"
                )

                if item_exists:
                    item_name = controller.server.get_message(
                        f"/browser/filter/{filter_idx}/item/{item_idx}/name"
                    )
                    is_selected = controller.server.get_message(
                        f"/browser/filter/{filter_idx}/item/{item_idx}/isSelected"
                    )
                    hits = controller.server.get_message(
                        f"/browser/filter/{filter_idx}/item/{item_idx}/hits"
                    )

                    status = ""
                    if is_selected:
                        status = "SELECTED"
                        selected_item = item_name

                    hits_str = f", hits: {hits}" if hits is not None else ""
                    logger.info(f"    {item_idx}: {item_name}{hits_str} {status}")

                    # Store item info
                    filter_info["items"][item_idx] = {
                        "name": item_name,
                        "selected": is_selected,
                        "hits": hits,
                    }

            logger.info(f"  Selected: {selected_item}")
            filter_info["selected_item"] = selected_item
            browser_filters[filter_idx] = filter_info

    return browser_filters


async def find_device_type_filter(controller: BitwigOSCController) -> Optional[int]:
    """Find the Device Type filter index.

    Args:
        controller: BitwigOSCController instance connected to Bitwig

    Returns:
        Optional[int]: Filter index for Device Type or None if not found
    """
    logger.info("\nLooking for Device Type filter...")

    # Find Device Type filter if it exists
    device_type_filter = None
    for filter_idx in range(1, 7):
        filter_name = controller.server.get_message(
            f"/browser/filter/{filter_idx}/name"
        )
        if filter_name == "Device Type":
            device_type_filter = filter_idx
            logger.info(f"Found Device Type filter at index {filter_idx}")
            break

    return device_type_filter


async def navigate_filter(
    controller: BitwigOSCController, filter_idx: int, direction: str = "+"
) -> Optional[str]:
    """Navigate a specific filter and return the newly selected item.

    Args:
        controller: BitwigOSCController instance connected to Bitwig
        filter_idx: The index of the filter to navigate
        direction: Navigation direction, "+" for next, "-" for previous

    Returns:
        Optional[str]: Name of the newly selected item or None
    """
    logger.info(f"\nNavigating filter {filter_idx} ({direction})...")

    # Navigate the filter
    controller.client.navigate_browser_filter(filter_idx, direction)
    await asyncio.sleep(0.5)

    # Find the newly selected item
    for item_idx in range(1, 17):
        is_selected = controller.server.get_message(
            f"/browser/filter/{filter_idx}/item/{item_idx}/isSelected"
        )
        if is_selected:
            item_name = controller.server.get_message(
                f"/browser/filter/{filter_idx}/item/{item_idx}/name"
            )
            logger.info(f"New selection: {item_name} (item {item_idx})")
            return item_name

    return None


def get_devices_on_current_page(controller: BitwigOSCController) -> List[str]:
    """Get all devices on the current browser page.

    Args:
        controller: BitwigOSCController instance connected to Bitwig

    Returns:
        List[str]: List of device names on the current page
    """
    devices = []

    # Check each result position (up to 50)
    for i in range(1, 51):
        result_exists = controller.server.get_message(f"/browser/result/{i}/exists")
        if not result_exists:
            # Show limited number of missing results to avoid clutter
            if i <= 20 or i % 5 == 0:
                logger.debug(f"No result at index {i}")
            if i > 20 and len(devices) == 0:
                break
            continue

        # Get device name
        result_name = controller.server.get_message(f"/browser/result/{i}/name")
        is_selected = controller.server.get_message(f"/browser/result/{i}/isSelected")
        status = " (SELECTED)" if is_selected else ""
        logger.debug(f"Result {i}: {result_name}{status}")
        devices.append(result_name)

    return devices


async def check_browser_tabs(
    controller: BitwigOSCController, max_attempts: int = 15
) -> Tuple[bool, Optional[str], List[str]]:
    """Find a browser tab with devices.

    Args:
        controller: BitwigOSCController instance connected to Bitwig
        max_attempts: Maximum number of tab navigation attempts

    Returns:
        Tuple[bool, Optional[str], List[str]]: Success status, tab name, and list of devices
    """
    logger.info("Searching for a browser tab with devices...")

    # Try to cycle through tabs until we find one with devices
    devices_found = False
    current_tab_name = None
    devices = []

    for attempt in range(max_attempts):
        # Check current tab
        current_tab_name = controller.server.get_message("/browser/tab")
        logger.info(f"Current tab ({attempt+1}): {current_tab_name}")

        # Check if the current tab has any results
        devices = get_devices_on_current_page(controller)

        if len(devices) > 0:
            logger.info(f"Found tab with {len(devices)} devices: {current_tab_name}")
            for i, device in enumerate(devices[:5], 1):  # Show first 5 devices
                logger.info(f"  Device {i}: {device}")
            devices_found = True
            break

        # Try next tab
        logger.info("No devices in current tab, trying next tab...")
        controller.client.navigate_browser_tab("+")
        await asyncio.sleep(0.5)

    if not devices_found:
        logger.warning("Could not find a tab with devices after multiple attempts")
        logger.info("Trying to reset filters as fallback...")

        # Reset all filters to make sure we'll get results
        for i in range(1, 7):  # There are typically 6 filters
            try:
                controller.client.reset_browser_filter(i)
                await asyncio.sleep(0.2)
            except Exception as e:
                logger.warning(f"Error resetting filter {i}: {e}")

        await asyncio.sleep(1.0)  # Wait for filters to reset

        # Check again for devices
        devices = get_devices_on_current_page(controller)
        if len(devices) > 0:
            logger.info(f"Found {len(devices)} devices after resetting filters")
            devices_found = True
        else:
            logger.warning("Still no devices found")

    return devices_found, current_tab_name, devices


async def print_browser_statistics(controller: BitwigOSCController) -> Dict[str, Any]:
    """Print comprehensive browser statistics.

    Args:
        controller: BitwigOSCController instance connected to Bitwig

    Returns:
        Dict: Statistics about browser state
    """
    stats = {}

    # Check browser state
    browser_active = controller.server.get_message("/browser/isActive")
    browser_exists = controller.server.get_message("/browser/exists")
    current_tab = controller.server.get_message("/browser/tab")

    logger.info("\nBrowser Status:")
    logger.info(f"- Browser active: {browser_active}")
    logger.info(f"- Browser exists: {browser_exists}")
    logger.info(f"- Current tab: {current_tab}")

    stats["browser_active"] = browser_active
    stats["browser_exists"] = browser_exists
    stats["current_tab"] = current_tab

    # Check filters
    filter_count = 0
    filters = {}

    logger.info("\nBrowser Filters:")
    for i in range(1, 7):
        filter_exists = controller.server.get_message(f"/browser/filter/{i}/exists")
        if filter_exists:
            filter_count += 1
            filter_name = controller.server.get_message(f"/browser/filter/{i}/name")
            logger.info(f"- Filter {i}: {filter_name}")

            filters[i] = {"name": filter_name, "selected_items": []}

            # Check selected items in this filter
            for j in range(1, 17):
                item_exists = controller.server.get_message(
                    f"/browser/filter/{i}/item/{j}/exists"
                )
                if item_exists:
                    item_selected = controller.server.get_message(
                        f"/browser/filter/{i}/item/{j}/isSelected"
                    )
                    if item_selected:
                        item_name = controller.server.get_message(
                            f"/browser/filter/{i}/item/{j}/name"
                        )
                        logger.info(f"  - Selected: {item_name}")
                        filters[i]["selected_items"].append(item_name)

    stats["filter_count"] = filter_count
    stats["filters"] = filters

    # Check results
    devices = get_devices_on_current_page(controller)

    logger.info(f"\nFound {len(devices)} browser results")
    if len(devices) > 0:
        for i, device in enumerate(devices[:10], 1):
            logger.info(f"- Result {i}: {device}")

        if len(devices) > 10:
            logger.info(f"- ... and {len(devices) - 10} more")

    stats["result_count"] = len(devices)
    stats["results"] = devices

    return stats


async def run_browser_diagnostic() -> None:
    """Run a comprehensive browser diagnostic session."""
    logger.info("\nRunning Bitwig Browser Diagnostics")
    logger.info("=" * 60)

    # Create controller
    controller = BitwigOSCController()
    controller.start()

    try:
        # Wait for connection
        logger.info("Establishing connection...")
        await asyncio.sleep(2.0)

        # Verify connection
        controller.client.refresh()
        await asyncio.sleep(0.5)
        tempo = controller.server.get_message("/tempo/raw")

        if tempo is None:
            logger.error(
                "Could not connect to Bitwig Studio - it might not be responding"
            )
            return

        logger.info(f"Connected to Bitwig Studio (tempo: {tempo} BPM)")

        # Open browser
        logger.info("\nOpening browser...")
        controller.client.browse_for_device("after")
        await asyncio.sleep(2.0)

        browser_active = controller.server.get_message("/browser/isActive")
        if not browser_active:
            logger.error("Failed to open browser")
            return

        # Find a tab with devices
        devices_found, tab_name, devices = await check_browser_tabs(controller)

        if devices_found:
            # Run detailed checks
            logger.info("\nRunning detailed browser checks...")

            # Check filters
            filters = await inspect_filters(controller)
            logger.info(f"Found {len(filters)} active filters")

            # Print statistics
            await print_browser_statistics(controller)

            # Try to find device type filter and navigate it
            device_type_filter = await find_device_type_filter(controller)
            if device_type_filter:
                await navigate_filter(controller, device_type_filter, "+")

        # Close browser
        logger.info("\nClosing browser...")
        controller.client.cancel_browser()
        await asyncio.sleep(0.5)

    finally:
        # Clean up
        controller.stop()
        logger.info("Done.")


if __name__ == "__main__":
    asyncio.run(run_browser_diagnostic())
