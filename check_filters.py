#!/usr/bin/env python
"""
Check filter structure in Bitwig browser
"""

import asyncio
from bitwig_mcp_server.osc.controller import BitwigOSCController


async def check_filters():
    print("\nBitwig Browser Filter Inspector")
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

        # Detailed filter inspection
        print("\nDetailed filter inspection:")
        for filter_idx in range(1, 7):
            filter_exists = controller.server.get_message(
                f"/browser/filter/{filter_idx}/exists"
            )

            if filter_exists:
                filter_name = controller.server.get_message(
                    f"/browser/filter/{filter_idx}/name"
                )
                print(f"\nFilter {filter_idx}: {filter_name}")

                # Examine all items in this filter
                print("  Items:")

                # Check which item is currently selected
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
                        print(f"    {item_idx}: {item_name}{hits_str} {status}")

                print(f"  Selected: {selected_item}")

        # Check results
        print("\nCurrent Results:")
        for i in range(1, 11):  # Show first 10 results
            result_exists = controller.server.get_message(f"/browser/result/{i}/exists")
            if result_exists:
                result_name = controller.server.get_message(f"/browser/result/{i}/name")
                is_selected = controller.server.get_message(
                    f"/browser/result/{i}/isSelected"
                )
                status = " (SELECTED)" if is_selected else ""
                print(f"  {i}: {result_name}{status}")

        # Test changing filter
        print("\nTesting filter navigation...")

        # Find Device Type filter if it exists
        device_type_filter = None
        for filter_idx in range(1, 7):
            filter_name = controller.server.get_message(
                f"/browser/filter/{filter_idx}/name"
            )
            if filter_name == "Device Type":
                device_type_filter = filter_idx
                print(f"Found Device Type filter at index {filter_idx}")
                break

        if device_type_filter:
            print(f"\nNavigating Device Type filter ({device_type_filter})...")

            # Reset filter first
            controller.client.reset_browser_filter(device_type_filter)
            await asyncio.sleep(0.5)

            # Navigate to the next item
            print("Selecting next item...")
            controller.client.navigate_browser_filter(device_type_filter, "+")
            await asyncio.sleep(0.5)

            # Check what changed
            for item_idx in range(1, 17):
                is_selected = controller.server.get_message(
                    f"/browser/filter/{device_type_filter}/item/{item_idx}/isSelected"
                )
                if is_selected:
                    item_name = controller.server.get_message(
                        f"/browser/filter/{device_type_filter}/item/{item_idx}/name"
                    )
                    print(f"New selection: {item_name} (item {item_idx})")
                    break

        # Close browser
        print("\nClosing browser...")
        controller.client.cancel_browser()

    finally:
        # Clean up
        controller.stop()
        print("Done.")


if __name__ == "__main__":
    asyncio.run(check_filters())
