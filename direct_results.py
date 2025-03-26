#!/usr/bin/env python
"""
Direct browser results check for Bitwig
"""

import asyncio
from bitwig_mcp_server.osc.controller import BitwigOSCController


async def check_direct_results():
    print("\nBitwig Browser Direct Results Check")
    print("=" * 60)

    # Create controller
    controller = BitwigOSCController()
    controller.start()

    try:
        # Wait for connection
        print("Establishing connection...")
        await asyncio.sleep(2.0)

        print("\nOpening browser...")
        controller.client.browse_for_device("after")
        await asyncio.sleep(2.0)

        # Check browser status directly
        browser_active = controller.server.get_message("/browser/isActive")
        print(f"Browser active: {browser_active}")

        # Check for results without doing any navigation
        print("\nChecking for results directly...")

        # Extract metadata for device result 1 as an example
        result_exists = controller.server.get_message("/browser/result/1/exists")
        print(f"Result 1 exists: {result_exists}")

        if result_exists:
            name = controller.server.get_message("/browser/result/1/name")
            print(f"Result 1 name: {name}")

        # Try navigating this result to see if we can get more results
        print("\nTrying to select result 1...")
        controller.client.navigate_browser_result("+")
        await asyncio.sleep(1.0)

        # Check if selection happened
        result1_selected = controller.server.get_message("/browser/result/1/isSelected")
        print(f"Result 1 selected: {result1_selected}")

        # Check for more results
        print("\nChecking for additional results...")
        for i in range(1, 21):
            exists = controller.server.get_message(f"/browser/result/{i}/exists")
            if exists:
                name = controller.server.get_message(f"/browser/result/{i}/name")
                selected = controller.server.get_message(
                    f"/browser/result/{i}/isSelected"
                )
                print(f"Result {i}: {name} (selected: {selected})")
            else:
                print(f"No result at index {i}")
                break

        # Check current tab
        current_tab = controller.server.get_message("/browser/tab")
        print(f"\nCurrent tab: {current_tab}")

        # Close browser
        print("\nClosing browser...")
        controller.client.cancel_browser()

    finally:
        # Clean up
        controller.stop()
        print("Done.")


if __name__ == "__main__":
    asyncio.run(check_direct_results())
