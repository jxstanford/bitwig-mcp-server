#!/usr/bin/env python
"""
Test script for browser result pagination in Bitwig Studio

This script tests the new pagination functionality in the OSC client
to ensure we can navigate through multiple pages of results.
"""

import asyncio
from bitwig_mcp_server.osc.controller import BitwigOSCController


async def test_browser_pagination():
    print("\nBitwig Browser Pagination Test")
    print("=" * 60)

    # Create controller
    controller = BitwigOSCController()
    controller.start()

    try:
        # Wait for connection
        await asyncio.sleep(2.0)
        print("Connected to Bitwig Studio")

        # Open the browser
        print("\nOpening browser...")
        controller.client.browse_for_device("after")
        await asyncio.sleep(2.0)

        # Check if browser opened
        browser_active = controller.server.get_message("/browser/isActive")
        print(f"Browser active: {browser_active}")

        if not browser_active:
            print("Browser did not open. Aborting.")
            return

        # Collect results from each page
        max_pages = 5  # Try up to 5 pages
        total_results = 0

        for page in range(max_pages):
            print(f"\n--- Page {page + 1} ---")

            # Count results on this page
            page_results = 0

            # Check each result position (1-16)
            for i in range(1, 17):
                result_exists = controller.server.get_message(
                    f"/browser/result/{i}/exists"
                )
                if not result_exists:
                    break

                result_name = controller.server.get_message(f"/browser/result/{i}/name")
                print(f"Result {i}: {result_name}")
                page_results += 1

            print(f"Found {page_results} results on page {page + 1}")
            total_results += page_results

            # If we found fewer than 16 results, we've reached the end
            if page_results < 16:
                print("End of results reached")
                break

            # Navigate to the next page
            print(f"Moving to page {page + 2}...")
            controller.client.select_next_browser_result_page()
            await asyncio.sleep(1.0)  # Wait for page to load

        print(f"\nTotal results found across all pages: {total_results}")

        # Navigate back to first page
        print("\nNavigating back to first page...")
        for _ in range(max_pages):
            controller.client.select_previous_browser_result_page()
            await asyncio.sleep(0.3)

        # Close browser
        print("\nClosing browser...")
        controller.client.cancel_browser()

    finally:
        # Clean up
        controller.stop()
        print("Test complete.")


if __name__ == "__main__":
    asyncio.run(test_browser_pagination())
