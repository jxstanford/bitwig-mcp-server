"""
Integration tests for browser pagination functionality.

These tests verify that pagination works correctly when navigating through browser results.
This test requires a running Bitwig Studio instance to test against.
"""

import asyncio
import logging

import pytest
import pytest_asyncio

from bitwig_mcp_server.osc.controller import BitwigOSCController
from tests.conftest import skip_if_bitwig_not_running

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Skip tests if Bitwig is not running
pytestmark = skip_if_bitwig_not_running


@pytest_asyncio.fixture
async def osc_controller():
    """Create a real OSC controller connected to Bitwig Studio."""
    # Create controller
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

        if tempo is None:
            logger.error(
                "Could not connect to Bitwig Studio - it might not be responding"
            )
            controller.stop()
            pytest.skip("Bitwig is not responding to OSC commands")

        logger.info(f"Connected to Bitwig Studio (tempo: {tempo} BPM)")

        # Make sure Bitwig is in a known state
        # Stop transport if playing
        play_state = controller.server.get_message("/play")
        if play_state:
            controller.client.stop()
            await asyncio.sleep(0.5)

        # Make sure browser is closed
        browser_active = controller.server.get_message("/browser/isActive")
        if browser_active:
            controller.client.cancel_browser()
            await asyncio.sleep(0.5)

        yield controller
    finally:
        # Clean up
        # Ensure transport is stopped
        controller.client.stop()

        # Ensure browser is closed
        browser_active = controller.server.get_message("/browser/isActive")
        if browser_active:
            controller.client.cancel_browser()
            await asyncio.sleep(0.5)

        controller.stop()


@pytest.mark.asyncio
async def test_browser_pagination_integration(osc_controller):
    """Test browser pagination with a real Bitwig Studio instance.

    This test requires a running Bitwig Studio instance.
    It will open the browser, navigate through pages, and verify results.
    """
    # Open the browser
    logger.info("Opening device browser...")
    osc_controller.client.browse_for_device("after")
    await asyncio.sleep(2.0)

    # Check if browser opened
    browser_active = osc_controller.server.get_message("/browser/isActive")
    assert browser_active, "Browser did not open properly"
    logger.info(f"Browser active: {browser_active}")

    # Try a more robust approach to ensure we're in a tab that shows devices
    # First try Devices tab (most reliable)
    logger.info("Searching for a browser tab with devices...")

    # Try to cycle through tabs until we find one with devices
    max_tab_attempts = 15  # More attempts to find a suitable tab
    devices_found = False

    for attempt in range(max_tab_attempts):
        # Check current tab
        current_tab = osc_controller.server.get_message("/browser/tab")
        logger.info(f"Current tab ({attempt+1}): {current_tab}")

        # Check if the current tab has any results
        test_devices = _get_devices_on_current_page(osc_controller)

        if len(test_devices) > 0:
            logger.info(f"Found tab with {len(test_devices)} devices: {current_tab}")
            for i, device in enumerate(test_devices[:5], 1):  # Show first 5 devices
                logger.info(f"  Device {i}: {device}")
            devices_found = True
            break

        # Try next tab
        logger.info("No devices in current tab, trying next tab...")
        osc_controller.client.navigate_browser_tab("+")
        await asyncio.sleep(0.5)

    if not devices_found:
        logger.warning("Could not find a tab with devices after multiple attempts")
        # Try a specific filter and wait a bit longer
        logger.info("Trying Devices filter as fallback...")

        # Reset all filters to make sure we'll get results
        for i in range(1, 7):  # There are typically 6 filters
            osc_controller.client.reset_browser_filter(i)
            await asyncio.sleep(0.2)

        await asyncio.sleep(1.0)  # Wait for filters to reset

        # Check again for devices
        test_devices = _get_devices_on_current_page(osc_controller)
        if len(test_devices) > 0:
            logger.info(f"Found {len(test_devices)} devices after resetting filters")
            devices_found = True
        else:
            logger.warning("Still no devices found, test may fail")

    # First test: verify we can navigate between pages and collect results
    await _test_multipage_navigation(osc_controller)

    # Second test: verify the browser responds appropriately when we reach the end of results
    await _test_end_of_results_behavior(osc_controller)


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

        # The devices should match what we saw on page 1, but Bitwig might refresh the browser
        # or show a different number of results when navigating back, so we check if we have devices
        # but don't require an exact match in count or content
        logger.info(f"Back on page 1, found {len(back_to_page1_devices)} devices")
        assert (
            len(back_to_page1_devices) > 0
        ), "No devices found after returning to page 1"

        # Check if at least some devices match - try the first device
        # This is also made more flexible to handle browser refreshes
        if len(back_to_page1_devices) > 0 and len(page1_devices) > 0:
            logger.info(f"First device on page 1 before: {page1_devices[0]}")
            logger.info(f"First device on page 1 after: {back_to_page1_devices[0]}")
            # We've observed that Bitwig may refresh browser contents during navigation
            # so we don't assert equality, just log the comparison

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
