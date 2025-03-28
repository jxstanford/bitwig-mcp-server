"""
Integration tests for browser pagination functionality

These tests verify that pagination works correctly when navigating through browser results.
This test requires a running Bitwig Studio instance to test against.
"""

import asyncio
import pytest
import logging

from bitwig_mcp_server.osc.controller import BitwigOSCController

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@pytest.mark.asyncio
@pytest.mark.realbitwig  # Mark as requiring a real Bitwig instance
async def test_live_browser_pagination():
    """Test browser pagination with a real Bitwig Studio instance.

    This test requires a running Bitwig Studio instance.
    It will open the browser, navigate through pages, and verify results.
    """
    # Create a real controller connected to Bitwig
    controller = BitwigOSCController()
    controller.start()

    try:
        # Allow time for connection
        logger.info("Connecting to Bitwig Studio...")
        await asyncio.sleep(2.0)

        # Verify connection
        controller.client.refresh()
        await asyncio.sleep(0.5)
        tempo = controller.server.get_message("/tempo/raw")
        assert tempo is not None, "Could not connect to Bitwig Studio. Is it running?"
        logger.info(f"Connected to Bitwig Studio (tempo: {tempo} BPM)")

        # Open the browser
        logger.info("Opening device browser...")
        controller.client.browse_for_device("after")
        await asyncio.sleep(2.0)

        # Check if browser opened
        browser_active = controller.server.get_message("/browser/isActive")
        assert browser_active, "Browser did not open properly"
        logger.info(f"Browser active: {browser_active}")

        # Navigate to the main results tab if needed
        current_tab = controller.server.get_message("/browser/tab")
        logger.info(f"Current browser tab: {current_tab}")

        target_tabs = ["Result", "Everything", "Devices"]  # Possible target tab names
        if current_tab not in target_tabs:
            # Try to find a suitable tab
            max_attempts = 10
            found_target = False

            for attempt in range(max_attempts):
                controller.client.navigate_browser_tab("+")
                await asyncio.sleep(0.5)
                current_tab = controller.server.get_message("/browser/tab")
                logger.info(f"Tab {attempt+1}: {current_tab}")

                if current_tab in target_tabs:
                    found_target = True
                    logger.info(f"Found target tab: {current_tab}")
                    break

            if not found_target:
                logger.warning(f"Could not find one of the target tabs: {target_tabs}")
                logger.warning(f"Continuing with current tab: {current_tab}")

        # First test: verify we can navigate between pages and collect results
        await _test_multipage_navigation(controller)

        # Second test: verify the browser responds appropriately when we reach the end of results
        await _test_end_of_results_behavior(controller)

    finally:
        # Clean up
        controller.client.cancel_browser()
        await asyncio.sleep(0.5)
        controller.stop()


async def _test_multipage_navigation(controller):
    """Test navigation through multiple pages of browser results."""
    logger.info("\n=== Testing multi-page navigation ===")

    # Test pagination through at least 2 pages
    total_devices = 0
    devices_by_page = []

    # First page
    logger.info("Examining page 1:")
    page1_devices = _get_devices_on_current_page(controller)
    devices_by_page.append(page1_devices)
    total_devices += len(page1_devices)

    # Log the devices found
    for i, device in enumerate(page1_devices, 1):
        logger.info(f"  Result {i}: {device}")
    logger.info(f"Found {len(page1_devices)} devices on page 1")

    # If we found exactly 16 devices, there might be more pages
    if len(page1_devices) == 16:
        # Try navigating to page 2
        logger.info("Moving to page 2...")
        controller.client.select_next_browser_result_page()
        await asyncio.sleep(1.0)

        # Get devices on page 2
        logger.info("Examining page 2:")
        page2_devices = _get_devices_on_current_page(controller)
        devices_by_page.append(page2_devices)
        total_devices += len(page2_devices)

        # Log the devices found
        for i, device in enumerate(page2_devices, 1):
            logger.info(f"  Result {i}: {device}")
        logger.info(f"Found {len(page2_devices)} devices on page 2")

        # Verify we got at least some devices on page 2
        assert len(page2_devices) > 0, "No devices found on page 2"

        # Navigate back to page 1
        logger.info("Navigating back to page 1...")
        controller.client.select_previous_browser_result_page()
        await asyncio.sleep(1.0)

        # Verify we're back on page 1 by checking devices
        back_to_page1_devices = _get_devices_on_current_page(controller)

        # The devices should match what we saw on page 1
        logger.info(f"Back on page 1, found {len(back_to_page1_devices)} devices")
        assert len(back_to_page1_devices) == len(
            page1_devices
        ), "Device count mismatch after returning to page 1"

        # Check if at least the first device matches
        if len(back_to_page1_devices) > 0 and len(page1_devices) > 0:
            assert (
                back_to_page1_devices[0] == page1_devices[0]
            ), "First device doesn't match after returning to page 1"

    logger.info(f"Total devices found across all pages: {total_devices}")
    assert total_devices > 0, "No devices found during pagination test"


async def _test_end_of_results_behavior(controller):
    """Test behavior when navigating past the end of available results."""
    logger.info("\n=== Testing end-of-results behavior ===")

    # Navigate to the first page
    logger.info("Returning to first page...")
    # Go back several times to ensure we're at the beginning
    for _ in range(5):
        controller.client.select_previous_browser_result_page()
        await asyncio.sleep(0.3)

    # Count the pages until we run out of results
    max_pages = 10  # Safety limit
    page_count = 0
    total_devices = 0
    has_more_pages = True

    # Keep navigating forward until we find a page with no results
    # or hit our safety limit
    while has_more_pages and page_count < max_pages:
        page_count += 1
        logger.info(f"Examining page {page_count}:")

        # Get devices on current page
        devices = _get_devices_on_current_page(controller)
        logger.info(f"Found {len(devices)} devices on page {page_count}")
        total_devices += len(devices)

        # If no devices on this page, or fewer than 16, we've reached the end
        if len(devices) == 0:
            logger.info(
                f"No devices found on page {page_count}, end of results reached"
            )
            has_more_pages = False
        elif len(devices) < 16:
            logger.info(
                f"Only {len(devices)} devices on page {page_count}, likely last page"
            )
            has_more_pages = False
        else:
            # Try to navigate to the next page
            logger.info(f"Moving to page {page_count + 1}...")
            controller.client.select_next_browser_result_page()
            await asyncio.sleep(1.0)

    logger.info(f"Total pages found: {page_count}")
    logger.info(f"Total devices found: {total_devices}")

    if page_count >= max_pages:
        logger.warning(
            f"Hit safety limit of {max_pages} pages, may not have reached end of results"
        )

    assert total_devices > 0, "No devices found during end-of-results test"


def _get_devices_on_current_page(controller):
    """Helper function to get all devices on the current browser page."""
    devices = []

    # Check each result position (1-16)
    for i in range(1, 17):
        result_exists = controller.server.get_message(f"/browser/result/{i}/exists")
        if not result_exists:
            break

        # Get device name
        result_name = controller.server.get_message(f"/browser/result/{i}/name")
        devices.append(result_name)

    return devices
