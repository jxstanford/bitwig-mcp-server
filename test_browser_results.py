#!/usr/bin/env python
"""
Test browser results directly
"""

import asyncio
from bitwig_mcp_server.osc.controller import BitwigOSCController


async def check_browser_results():
    print("\nBitwig Browser Results Test")
    print("=" * 60)

    # Create and start controller
    controller = BitwigOSCController()
    controller.start()

    try:
        # Wait for connection
        await asyncio.sleep(2.0)

        # Open the browser
        print("Opening browser...")
        controller.client.browse_for_device("after")
        await asyncio.sleep(2.0)

        browser_active = controller.server.get_message("/browser/isActive")
        print(f"Browser active: {browser_active}")

        # Check browser filters
        print("\nBrowser filters:")
        for i in range(1, 7):
            filter_exists = controller.server.get_message(f"/browser/filter/{i}/exists")
            if filter_exists:
                filter_name = controller.server.get_message(f"/browser/filter/{i}/name")
                print(f"- Filter {i}: {filter_name}")

                # Check selected items
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
                            print(f"  - Selected: {item_name}")

        # Check browser results directly one by one
        print("\nChecking browser results directly:")
        result_count = 0
        for i in range(1, 50):  # Check up to 50 results
            result_exists = controller.server.get_message(f"/browser/result/{i}/exists")
            if result_exists:
                result_count += 1
                result_name = controller.server.get_message(f"/browser/result/{i}/name")
                print(f"{i}: {result_name}")
            else:
                print(f"No result at index {i}")
                # Only show 3 non-results before stopping
                if i > result_count + 3:
                    break

        print(f"\nFound {result_count} browser results")

        # Try to select a result if any were found
        if result_count > 0:
            print("\nSelecting first result...")
            controller.client.navigate_browser_result("+")
            await asyncio.sleep(0.5)
            selected = controller.server.get_message("/browser/result/1/isSelected")
            print(f"Result 1 selected: {selected}")

        # Close browser
        print("\nClosing browser...")
        controller.client.cancel_browser()

    finally:
        # Clean up
        controller.stop()
        print("Done.")


if __name__ == "__main__":
    asyncio.run(check_browser_results())
