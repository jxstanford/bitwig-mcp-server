#!/usr/bin/env python
"""Test script for browser commands"""

import asyncio
from bitwig_mcp_server.osc.controller import BitwigOSCController


async def test_browser():
    print("\nBitwig Browser Test Script")
    print("=" * 60)
    print("This script will test browser-related OSC commands with Bitwig Studio")
    print("=" * 60)

    # Create and start the controller
    controller = BitwigOSCController()
    controller.start()

    try:
        # Wait for connection
        print("\nEstablishing connection...")
        await asyncio.sleep(2.0)

        # Refresh to get initial state
        controller.client.refresh()
        await asyncio.sleep(1.0)

        # Check basic OSC functionality
        tempo = controller.server.get_message("/tempo/raw")
        print(f"Tempo: {tempo}")
        if tempo is None:
            print(
                "WARNING: Cannot get tempo. Bitwig may not be responding to OSC commands."
            )
            print(
                "Please check your Bitwig OSC controller setup and restart this test."
            )
            return

        # Test 1: Open the browser
        print("\nTest 1: Opening the browser")
        print("-" * 60)
        print("Sending browse_for_device('after') command...")
        controller.client.browse_for_device("after")
        await asyncio.sleep(2.0)

        # Check browser state
        print("\nChecking browser state:")
        browser_active = controller.server.get_message("/browser/isActive")
        print(f"- Browser active (/browser/isActive): {browser_active}")
        browser_exists = controller.server.get_message("/browser/exists")
        print(f"- Browser exists (/browser/exists): {browser_exists}")
        browser_tab = controller.server.get_message("/browser/tab")
        print(f"- Browser tab (/browser/tab): {browser_tab}")

        # Test 2: Navigate tabs
        print("\nTest 2: Navigating browser tabs")
        print("-" * 60)
        print("Sending navigate_browser_tab('+') command...")
        controller.client.navigate_browser_tab("+")
        await asyncio.sleep(1.0)
        new_tab = controller.server.get_message("/browser/tab")
        print(f"- New tab after navigation: {new_tab}")

        # Test 3: Check filters
        print("\nTest 3: Checking browser filters")
        print("-" * 60)
        filter_count = 0
        for i in range(1, 7):
            filter_exists = controller.server.get_message(f"/browser/filter/{i}/exists")
            if filter_exists:
                filter_count += 1
                filter_name = controller.server.get_message(f"/browser/filter/{i}/name")
                print(f"- Filter {i}: {filter_name} (exists: {filter_exists})")

                # Check filter items
                item_count = 0
                for j in range(1, 6):  # Just check first 5 items
                    item_exists = controller.server.get_message(
                        f"/browser/filter/{i}/item/{j}/exists"
                    )
                    if item_exists:
                        item_count += 1
                        item_name = controller.server.get_message(
                            f"/browser/filter/{i}/item/{j}/name"
                        )
                        item_selected = controller.server.get_message(
                            f"/browser/filter/{i}/item/{j}/isSelected"
                        )
                        print(f"  - Item {j}: {item_name} (selected: {item_selected})")

                print(f"  Found {item_count} items in filter {i}")

        print(f"Found {filter_count} filters in the browser")

        # Test 4: Check results
        print("\nTest 4: Checking browser results")
        print("-" * 60)
        result_count = 0
        for i in range(1, 11):  # Check first 10 results
            result_exists = controller.server.get_message(f"/browser/result/{i}/exists")
            if result_exists:
                result_count += 1
                result_name = controller.server.get_message(f"/browser/result/{i}/name")
                result_selected = controller.server.get_message(
                    f"/browser/result/{i}/isSelected"
                )
                print(f"- Result {i}: {result_name} (selected: {result_selected})")

        print(f"Found {result_count} results in the browser")

        # Test 5: Select filter items
        if filter_count > 0:
            print("\nTest 5: Selecting filter items")
            print("-" * 60)
            # Find a filter with items
            for i in range(1, 7):
                filter_exists = controller.server.get_message(
                    f"/browser/filter/{i}/exists"
                )
                if filter_exists:
                    filter_name = controller.server.get_message(
                        f"/browser/filter/{i}/name"
                    )
                    print(f"Testing filter {i}: {filter_name}")

                    # Navigate to first item
                    print(f"Sending navigate_browser_filter({i}, '+') command...")
                    controller.client.navigate_browser_filter(i, "+")
                    await asyncio.sleep(1.0)

                    # Check what changed
                    for j in range(1, 6):
                        item_selected = controller.server.get_message(
                            f"/browser/filter/{i}/item/{j}/isSelected"
                        )
                        if item_selected:
                            item_name = controller.server.get_message(
                                f"/browser/filter/{i}/item/{j}/name"
                            )
                            print(f"- Item {j} now selected: {item_name}")

                    break  # Just test one filter

        # Test 6: Close the browser
        print("\nTest 6: Closing the browser")
        print("-" * 60)
        print("Sending cancel_browser() command...")
        controller.client.cancel_browser()
        await asyncio.sleep(1.0)

        # Check browser state after closing
        browser_active = controller.server.get_message("/browser/isActive")
        print(f"- Browser active after closing: {browser_active}")

        # Results
        print("\nTest Results")
        print("=" * 60)

        if browser_active is None:
            print(
                "⚠️ Browser commands are not working properly with the Bitwig OSC controller"
            )
            print("Please check that:")
            print(
                "1. The Bitwig Studio Controller Script has browser OSC commands enabled"
            )
            print("2. You are using the latest version of the controller script")
            print("3. A project is open in Bitwig Studio")
        else:
            print("✅ Basic browser communication is working")

        if browser_tab is None:
            print("⚠️ Unable to detect browser tab state")

        if filter_count == 0:
            print("⚠️ No browser filters were detected")
        else:
            print(f"✅ Found {filter_count} browser filters")

        if result_count == 0:
            print("⚠️ No browser results were detected")
        else:
            print(f"✅ Found {result_count} browser results")

    finally:
        # Clean up
        print("\nCleaning up...")
        controller.stop()
        print("Test complete")


if __name__ == "__main__":
    asyncio.run(test_browser())
