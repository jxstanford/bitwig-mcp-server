#!/usr/bin/env python
"""
Browser tab explorer for Bitwig
"""

import asyncio
from bitwig_mcp_server.osc.controller import BitwigOSCController


async def explore_browser_tabs():
    print("\nBitwig Browser Tab Explorer")
    print("=" * 60)

    # Variable to store the first tab name for cycle detection
    saved_first_tab = None

    # Create controller
    controller = BitwigOSCController()
    controller.start()

    try:
        # Wait for connection
        await asyncio.sleep(2.0)

        # Open the browser
        print("Opening browser...")
        controller.client.browse_for_device("after")
        await asyncio.sleep(2.0)

        # Check if browser opened
        browser_active = controller.server.get_message("/browser/isActive")
        print(f"Browser active: {browser_active}")

        if not browser_active:
            print("Browser did not open. Aborting.")
            return

        # Explore tabs
        print("\nExploring browser tabs...")
        max_tabs = 10  # Maximum tabs to check

        for tab_idx in range(max_tabs):
            # Get current tab name
            current_tab = controller.server.get_message("/browser/tab")
            print(f"\nTab {tab_idx + 1}: {current_tab}")

            # Check how many results are in this tab
            device_count = 0
            for i in range(1, 31):  # Check first 30 results
                result_exists = controller.server.get_message(
                    f"/browser/result/{i}/exists"
                )
                if not result_exists:
                    break
                device_count += 1

            print(f"Found {device_count} results in this tab")

            if device_count > 0:
                # Show some results
                print("First few results:")
                for i in range(1, min(6, device_count + 1)):
                    device_name = controller.server.get_message(
                        f"/browser/result/{i}/name"
                    )
                    print(f"  {i}: {device_name}")

            # Navigate to next tab
            print("Navigating to next tab...")
            controller.client.navigate_browser_tab("+")
            await asyncio.sleep(1.0)

            # Check if we've looped back to the first tab
            if tab_idx > 0:
                new_tab = controller.server.get_message("/browser/tab")
                if new_tab == saved_first_tab:
                    print("Returned to first tab. Tab navigation complete.")
                    break

            # Store first tab for comparison
            if tab_idx == 0:
                saved_first_tab = current_tab

        # Close browser
        print("\nClosing browser...")
        controller.client.cancel_browser()

    finally:
        # Clean up
        controller.stop()
        print("Done.")


if __name__ == "__main__":
    asyncio.run(explore_browser_tabs())
