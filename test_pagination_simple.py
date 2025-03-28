#!/usr/bin/env python
"""
Simple test script for browser pagination in Bitwig

This is a minimal test that focuses solely on testing the browser pagination
functionality with a running Bitwig Studio instance.
"""

import asyncio
import logging

from bitwig_mcp_server.osc.controller import BitwigOSCController

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def test_pagination():
    """Test browser pagination with live Bitwig Studio instance"""
    print("\n=== Bitwig Browser Pagination Test ===")
    print("This test requires Bitwig Studio to be running.\n")

    # Create controller
    controller = BitwigOSCController()
    controller.start()

    try:
        # Wait for connection
        print("Connecting to Bitwig Studio...")
        await asyncio.sleep(2.0)

        # Verify connection by checking tempo
        controller.client.refresh()
        await asyncio.sleep(1.0)
        tempo = controller.server.get_message("/tempo/raw")

        if tempo is None:
            print("ERROR: Could not connect to Bitwig Studio. Is it running?")
            return
        print(f"Connected to Bitwig Studio (tempo: {tempo} BPM)")

        # Open the browser
        print("\nOpening device browser...")
        controller.client.browse_for_device("after")
        await asyncio.sleep(2.0)

        # Check if browser opened
        browser_active = controller.server.get_message("/browser/isActive")
        print(f"Browser active: {browser_active}")

        if not browser_active:
            print("ERROR: Browser did not open. Aborting test.")
            return

        # Get current tab
        current_tab = controller.server.get_message("/browser/tab")
        print(f"Current browser tab: {current_tab}")

        # Test navigation through pages
        total_devices = 0

        # Check devices on initial page
        print("\n--- Page 1 ---")
        page1_devices = []
        for i in range(1, 17):
            result_exists = controller.server.get_message(f"/browser/result/{i}/exists")
            if not result_exists:
                break

            result_name = controller.server.get_message(f"/browser/result/{i}/name")
            page1_devices.append(result_name)
            print(f"  Result {i}: {result_name}")

        print(f"Found {len(page1_devices)} devices on page 1")
        total_devices += len(page1_devices)

        # If we found devices on page 1, try moving to page 2
        if page1_devices:
            print("\nNavigating to page 2...")
            # Try the pagination feature
            controller.client.select_next_browser_result_page()
            await asyncio.sleep(1.0)

            # Check devices on page 2
            print("--- Page 2 ---")
            page2_devices = []
            for i in range(1, 17):
                result_exists = controller.server.get_message(
                    f"/browser/result/{i}/exists"
                )
                if not result_exists:
                    break

                result_name = controller.server.get_message(f"/browser/result/{i}/name")
                page2_devices.append(result_name)
                print(f"  Result {i}: {result_name}")

            print(f"Found {len(page2_devices)} devices on page 2")
            total_devices += len(page2_devices)

            # Return to page 1
            print("\nNavigating back to page 1...")
            controller.client.select_previous_browser_result_page()
            await asyncio.sleep(1.0)

            # Verify we're back on page 1
            back_to_page1 = []
            for i in range(1, 17):
                result_exists = controller.server.get_message(
                    f"/browser/result/{i}/exists"
                )
                if not result_exists:
                    break

                result_name = controller.server.get_message(f"/browser/result/{i}/name")
                back_to_page1.append(result_name)

            if back_to_page1 and page1_devices and back_to_page1[0] == page1_devices[0]:
                print("Successfully returned to page 1!")
            else:
                print("WARNING: Page 1 content may have changed after returning")

        # Report total
        print(f"\nTotal devices found: {total_devices}")

        # Close browser
        print("\nClosing browser...")
        controller.client.cancel_browser()
        await asyncio.sleep(1.0)

    except Exception as e:
        print(f"Error during test: {e}")

    finally:
        # Clean up
        controller.stop()
        print("\nTest completed.")


if __name__ == "__main__":
    asyncio.run(test_pagination())
