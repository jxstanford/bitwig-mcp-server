#!/usr/bin/env python3
"""
OSC Query Utility

A simple tool to send OSC commands to Bitwig Studio and retrieve the results.
This is useful for exploring the OSC interface and debugging communication issues.

Features:
- Query specific OSC addresses
- Send commands with values
- Use wildcard patterns to match multiple addresses:
  - '*' matches exactly one path segment
  - '**' matches any number of path segments
  - '?' matches a single character within a path segment
- List common OSC addresses
- Scan for active browser endpoints

Usage:
  python osc_query.py "/browser/tab/name/0"  # Query a specific OSC address
  python osc_query.py "/browser/isActive" 1  # Send a command with a value
  python osc_query.py "/browser/*/name"      # Use wildcard to match one path segment
  python osc_query.py "/browser/**/name"     # Use recursive wildcard to match any number of segments
  python osc_query.py --list                 # Show common OSC addresses
  python osc_query.py --scan-browser         # Scan for active browser endpoints
"""

import asyncio
import argparse
import logging
import sys
from typing import Any, Dict, Optional

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("osc_query")

# Add parent directory to path so we can import our modules
sys.path.append("..")

from bitwig_mcp_server.osc.controller import BitwigOSCController
from bitwig_mcp_server.settings import Settings


async def connect_to_bitwig() -> Optional[BitwigOSCController]:
    """Connect to Bitwig Studio via OSC.

    Returns:
        The OSC controller if connected, None otherwise
    """
    settings = Settings()
    controller = BitwigOSCController(
        ip=settings.bitwig_host,
        send_port=settings.bitwig_send_port,
        receive_port=settings.bitwig_receive_port,
    )

    try:
        # Start the controller
        controller.start()

        # Wait for connection
        await asyncio.sleep(2.0)

        # Try to get basic data from Bitwig
        controller.client.refresh()
        await asyncio.sleep(1.0)

        # Check if we're receiving data
        tempo = controller.server.get_message("/tempo/raw")
        project_name = controller.server.get_message("/project/name")

        if tempo is None and project_name is None:
            logger.error("❌ Could not connect to Bitwig Studio")
            logger.error(
                "Please make sure Bitwig Studio is running with a project open"
            )
            logger.error("and the OSC Controller extension is enabled")
            controller.stop()
            return None

        logger.info(f"✅ Connected to Bitwig Studio (project: {project_name})")
        return controller

    except Exception as e:
        logger.error(f"❌ Failed to connect to Bitwig Studio: {e}")
        if controller:
            try:
                controller.stop()
            except Exception:
                pass
        return None


async def query_osc_address(
    controller: BitwigOSCController, address: str, value: Optional[Any] = None
) -> Optional[Any]:
    """Query an OSC address and return the result.

    Args:
        controller: The OSC controller
        address: The OSC address to query
        value: Optional value to send with the address

    Returns:
        The result from the OSC server, or None if no result was received
    """
    # Clear existing messages for a clean slate
    controller.server.received_messages.clear()

    # First send a refresh to make sure we're getting latest data
    controller.client.refresh()
    await asyncio.sleep(0.5)

    # Send the actual query
    if value is not None:
        logger.info(f"Sending: {address} = {value}")
        controller.client.send(address, value)
    else:
        logger.info(f"Querying: {address}")
        # Some addresses need to be queried directly, others need to request a change
        controller.client.send(address, None)  # Try querying directly

    # Allow time for a response
    await asyncio.sleep(0.5)

    # Try several strategies to get the result

    # 1. Direct check for the exact address
    result = controller.server.get_message(address)
    if result is not None:
        return result

    # 2. If we're querying a specific index but getting no response, try without index
    if "/" in address and address.split("/")[-1].isdigit():
        # Try the base address without the index
        base_address = "/".join(address.split("/")[:-1])
        result = controller.server.get_message(base_address)
        if result is not None:
            return result

    # 3. Special handling for project name, tempo, etc.
    if address == "/project/name":
        special_addresses = [
            "/project/name",
            "/tempo/raw",
            "/play",
            "/record",
            "/overdub",
        ]
        for special_addr in special_addresses:
            special_result = controller.server.get_message(special_addr)
            if special_addr == address and special_result is not None:
                return special_result

        # If we're still here, try another refresh and wait longer
        controller.client.refresh()
        await asyncio.sleep(1.0)
        return controller.server.get_message(address)

    # If we're still here, see if ANY messages were received
    if controller.server.received_messages:
        # For debugging, return the first received message if it's related to our query
        # Handle case when address doesn't contain a slash
        address_parts = address.split("/")
        if len(address_parts) > 1:
            # Normal case with slashes
            address_segment = address_parts[1]
            for addr, val in controller.server.received_messages.items():
                if addr.startswith(address_segment):
                    logger.debug(f"Found related message: {addr} = {val}")
                    return val
        else:
            # Handle case when there's no slash in the address
            # Try to find any address containing our query string
            for addr, val in controller.server.received_messages.items():
                if address.lower() in addr.lower():
                    logger.debug(f"Found fuzzy match: {addr} = {val}")
                    return val

    # Nothing worked, return None
    return None


async def show_common_addresses(
    controller: BitwigOSCController, show_all: bool = True
) -> None:
    """Query and display common OSC addresses.

    Args:
        controller: The OSC controller
        show_all: Whether to show all received messages
    """
    # First make sure we have a complete refresh
    controller.client.refresh()
    await asyncio.sleep(1.0)

    # Send follow-up commands to get more data
    controller.client.send("/browser/show", 1)  # Try to open browser
    await asyncio.sleep(1.5)

    # Send another refresh
    controller.client.refresh()
    await asyncio.sleep(1.0)

    # Show all received messages if requested
    if show_all:
        logger.info("\nAll received OSC messages:")
        for addr, value in sorted(controller.server.received_messages.items()):
            logger.info(f"{addr}: {value}")

    # Now try some specific queries for key pieces of info
    logger.info("\nKey information:")
    key_addresses = [
        "/tempo/raw",
        "/project/name",
        "/play",
        "/record",
        "/browser/isActive",
        "/browser/tab",
    ]

    for address in key_addresses:
        value = controller.server.get_message(address)
        if value is not None:
            logger.info(f"{address}: {value}")

    # Try some browser-specific queries if browser seems to be active
    if controller.server.get_message("/browser/isActive") == 1:
        logger.info("\nBrowser is active, trying browser-specific queries:")
        browser_addresses = [
            "/browser/tab/name/0",
            "/browser/tab/name/1",
            "/browser/result/0",
            "/browser/filter/0/name",
        ]

        for address in browser_addresses:
            # For these, do a direct send and get
            controller.client.send(address, 1)
            await asyncio.sleep(0.5)
            value = controller.server.get_message(address)
            logger.info(f"{address}: {value}")


async def scan_browser_endpoints(
    controller: BitwigOSCController, show_all: bool = True
) -> None:
    """Scan for active browser-related OSC endpoints using a reliable approach.

    This tries various browser endpoints to see which ones are active.

    Args:
        controller: The OSC controller
        show_all: Whether to show all received messages
    """
    # Clear existing messages for a clean start
    controller.server.received_messages.clear()

    # Make sure browser is open, using the method from browser_indexer.py
    logger.info("Opening browser using browse_for_device method...")
    controller.client.browse_for_device("after")
    await asyncio.sleep(2.0)

    # Refresh and check if browser is active
    controller.client.refresh()
    await asyncio.sleep(1.0)

    # Check browser status
    is_active = controller.server.get_message("/browser/isActive")
    logger.info(f"Browser active: {is_active}")

    # If browser isn't active, try another method
    if not is_active or is_active != 1:
        logger.info("Browser not active, trying alternative method...")
        controller.client.send("/browser/show", 1)
        await asyncio.sleep(2.0)
        controller.client.refresh()
        await asyncio.sleep(1.0)
        is_active = controller.server.get_message("/browser/isActive")
        logger.info(f"Browser active after second attempt: {is_active}")

    # Report all received messages if requested
    if show_all:
        logger.info("\nAll messages after browser opening:")
        for addr, value in sorted(controller.server.received_messages.items()):
            logger.info(f"{addr}: {value}")

    # Tab and Navigation Direct Testing
    logger.info("\nTesting Tab Navigation...")

    # Try to navigate to first tab
    logger.info("Moving to first tab...")
    for _ in range(5):
        controller.client.send("/browser/tab/navigate", "-")
        await asyncio.sleep(0.3)

    # Check current tab
    controller.client.refresh()
    await asyncio.sleep(0.5)
    current_tab = controller.server.get_message("/browser/tab")
    logger.info(f"Current tab after navigation to first: {current_tab}")

    # Try moving to next tab
    logger.info("Moving to next tab...")
    controller.client.send("/browser/tab/navigate", "+")
    await asyncio.sleep(0.5)
    controller.client.refresh()
    await asyncio.sleep(0.5)
    next_tab = controller.server.get_message("/browser/tab")
    logger.info(f"Tab after moving to next: {next_tab}")

    # Try direct tab selection
    for i in range(3):  # Try a few tabs
        logger.info(f"Trying direct selection of tab {i}...")
        controller.client.send(f"/browser/tab/select/{i}", 1)
        await asyncio.sleep(0.5)
        controller.client.refresh()
        await asyncio.sleep(0.5)
        tab_after_select = controller.server.get_message("/browser/tab")
        logger.info(f"Tab after selecting index {i}: {tab_after_select}")

    # Check for filter columns on current tab
    logger.info("\nChecking filter columns...")
    for i in range(3):  # Check first few columns
        controller.client.send(f"/browser/filter/{i}/name", 1)
        await asyncio.sleep(0.5)
        filter_name = controller.server.get_message(f"/browser/filter/{i}/name")
        if filter_name:
            logger.info(f"Filter column {i}: {filter_name}")

            # Check some items in this filter
            for j in range(3):  # Check first few items
                controller.client.send(f"/browser/filter/{i}/item/{j}", 1)
                await asyncio.sleep(0.3)
                item_name = controller.server.get_message(
                    f"/browser/filter/{i}/item/{j}"
                )
                if item_name:
                    logger.info(f"  Filter item {j}: {item_name}")

    # Try searching for "Stereo Split"
    logger.info("\nSearching for 'Stereo Split'...")
    controller.client.send("/browser/search", "Stereo Split")
    await asyncio.sleep(1.5)

    # Check results
    logger.info("Checking results after search...")
    controller.client.refresh()
    await asyncio.sleep(0.5)

    # Try direct result access
    for i in range(3):  # Check first few results
        controller.client.send(f"/browser/result/{i}", 1)
        await asyncio.sleep(0.3)
        result_name = controller.server.get_message(f"/browser/result/{i}")
        if result_name:
            logger.info(f"Result {i}: {result_name}")

            # Get metadata for this result
            for prop in ["type", "category", "creator", "tags"]:
                controller.client.send(f"/browser/result/{i}/{prop}", 1)
                await asyncio.sleep(0.3)
                prop_value = controller.server.get_message(
                    f"/browser/result/{i}/{prop}"
                )
                if prop_value:
                    logger.info(f"  {prop}: {prop_value}")

    # Get all messages at the end for a comprehensive view if requested
    controller.client.refresh()
    await asyncio.sleep(1.0)

    if show_all:
        logger.info("\nAll messages at end of scan:")
        for addr, value in sorted(controller.server.received_messages.items()):
            if addr.startswith("/browser"):
                logger.info(f"{addr}: {value}")

    # Close the browser
    logger.info("\nClosing browser...")
    controller.client.cancel_browser()
    await asyncio.sleep(0.5)


async def query_osc_wildcard(
    controller: BitwigOSCController, pattern: str
) -> Dict[str, Any]:
    """Query OSC addresses matching a wildcard pattern.

    Args:
        controller: The OSC controller
        pattern: A wildcard pattern like:
                - "/browser/*/name" (matches exactly one path segment)
                - "/browser/**/name" (matches any number of path segments)

    Returns:
        A dictionary of matching addresses and their values
    """
    # First, clear existing messages
    controller.server.received_messages.clear()

    # Send a refresh to get current state
    controller.client.refresh()
    await asyncio.sleep(1.0)

    # Convert the pattern to a regex
    import re

    # Determine if pattern uses ** (recursive wildcard) or just * (single-level wildcard)
    has_recursive_wildcard = "**" in pattern

    # Count the number of segments in the pattern for exact matching
    pattern_parts = [p for p in pattern.split("/") if p and p != "**"]
    pattern_depth = len(pattern_parts)

    # Create a regex pattern based on the wildcard types
    pattern_regex = pattern

    # First replace ** (if any) with a placeholder that won't conflict with other replacements
    if has_recursive_wildcard:
        pattern_regex = pattern_regex.replace("**", "###RECURSIVE###")

    # Now handle single level wildcards (* and ?)
    pattern_regex = pattern_regex.replace("*", "[^/]*").replace("?", "[^/]")

    # Finally, handle recursive wildcards if present
    if has_recursive_wildcard:
        pattern_regex = pattern_regex.replace("###RECURSIVE###", ".*")

    # Add end anchor unless the pattern ends with ** (which means "match anything after")
    if not pattern.endswith("**"):
        pattern_regex += "$"

    # Create the regex object for matching
    regex = re.compile(pattern_regex)

    # Check if we need to run extra probing
    needs_browser_open = pattern.startswith("/browser")
    needs_track_probing = pattern.startswith("/track")

    # For browser wildcards, try to make sure browser is open
    if needs_browser_open:
        controller.client.browse_for_device("after")
        await asyncio.sleep(2.0)
        controller.client.refresh()
        await asyncio.sleep(1.0)

    # For specific patterns, try targeted probing based on the pattern
    if "*" in pattern:
        # Generate specific sample values to substitute for wildcards
        # This creates concrete paths to probe for matches
        probe_indices = list(range(5))  # Try up to 5 indices

        # Generate a list of paths to probe by replacing wildcards with concrete values
        probe_paths = []

        # First, check if we're dealing with filter paths
        if "/browser/filter/*" in pattern:
            # For /browser/filter/*/name
            if pattern.endswith("/name"):
                for i in probe_indices:
                    probe_paths.append(f"/browser/filter/{i}/name")
            # For /browser/filter/*/item/*/name
            elif "/item/" in pattern and pattern.endswith("/name"):
                for i in probe_indices:
                    for j in probe_indices:
                        probe_paths.append(f"/browser/filter/{i}/item/{j}/name")

        # Result paths
        elif "/browser/result/*" in pattern:
            if pattern.endswith("/*"):  # Just probe all results
                for i in probe_indices:
                    probe_paths.append(f"/browser/result/{i}")
            else:
                property_name = pattern.split("/")[-1]
                for i in probe_indices:
                    probe_paths.append(f"/browser/result/{i}/{property_name}")

        # Tab paths
        elif "/browser/tab/*" in pattern:
            for i in probe_indices:
                probe_paths.append(f"/browser/tab/name/{i}")

        # Track paths
        elif "/track/*" in pattern:
            for i in probe_indices:
                if pattern.endswith("/*"):  # Probe all track properties
                    for prop in ["name", "volume", "pan", "mute", "solo"]:
                        probe_paths.append(f"/track/{i}/{prop}")
                elif pattern.split("/")[-1] != "*":  # Specific property
                    property_name = pattern.split("/")[-1]
                    probe_paths.append(f"/track/{i}/{property_name}")

        # If we didn't generate specific paths, try generic probing
        if not probe_paths:
            # Try some common browser paths
            if needs_browser_open:
                for i in range(5):  # Try a few tabs
                    controller.client.send(f"/browser/tab/name/{i}", 1)
                    await asyncio.sleep(0.1)

                for i in range(5):  # Try a few filter columns
                    controller.client.send(f"/browser/filter/{i}/name", 1)
                    await asyncio.sleep(0.1)

                for i in range(5):  # Try a few results
                    controller.client.send(f"/browser/result/{i}", 1)
                    await asyncio.sleep(0.1)

            elif needs_track_probing:
                # Try some common track paths
                for i in range(5):  # Try a few tracks
                    controller.client.send(f"/track/{i}/name", 1)
                    controller.client.send(f"/track/{i}/volume", 1)
                    controller.client.send(f"/track/{i}/pan", 1)
                    await asyncio.sleep(0.1)
        else:
            # Send each probe path
            for path in probe_paths:
                controller.client.send(path, 1)
                await asyncio.sleep(0.1)

    # Wait a moment for responses
    await asyncio.sleep(1.0)

    # Filter the results based on the pattern
    matches = {}

    # Determine if we're using recursive matching or exact structure matching
    exact_structure = not has_recursive_wildcard

    # Match received messages against our pattern
    for addr, value in controller.server.received_messages.items():
        if regex.match(addr):
            if exact_structure and not pattern.endswith("*"):
                # In exact structure mode, verify the path has the right structure
                addr_parts = [p for p in addr.split("/") if p]
                if len(addr_parts) == pattern_depth:
                    matches[addr] = value
            else:
                # In recursive mode or if pattern ends with *, include all matching paths
                matches[addr] = value

    return matches


async def run_osc_query(args: argparse.Namespace) -> None:
    """Main function to run the OSC query.

    Args:
        args: Command line arguments
    """
    # Connect to Bitwig
    controller = await connect_to_bitwig()
    if not controller:
        return

    try:
        if args.list:
            # Show common addresses
            await show_common_addresses(controller, args.all_messages)
        elif args.scan_browser:
            # Scan browser endpoints
            await scan_browser_endpoints(controller, args.all_messages)
        else:
            # Special case for device searches (no slash prefix)
            if (
                not args.address.startswith("/")
                and len(args.address) >= 2
                and not args.value
            ):
                # This is likely a search for a device or parameter by name
                logger.info(f"Searching for: {args.address}")

                # ================ PART 1: Check Current Device ================
                # First check if we have a currently selected device that matches
                current_device_name = controller.server.get_message("/device/name")
                current_device_match = (
                    current_device_name
                    and args.address.lower() in current_device_name.lower()
                )

                if current_device_match:
                    logger.info(
                        f"✅ Currently selected device matches query: {current_device_name}"
                    )

                    # Get all available info about this device
                    logger.info("\n== DEVICE INFORMATION ==")
                    print(f"  Name: {current_device_name}")

                    # Get all device info using wildcard query
                    logger.info("Gathering all available device information...")

                    # Get all device information excluding parameters (we'll handle those separately)
                    device_info = await query_osc_wildcard(controller, "/device/**")

                    # Filter out parameter-related addresses since we'll handle them separately
                    device_props = {
                        k: v
                        for k, v in device_info.items()
                        if "/device/param/" not in k
                    }

                    # Display all device properties
                    for prop, value in sorted(device_props.items()):
                        print(f"  {prop} = {value}")

                    # Get all parameters
                    logger.info("\n== DEVICE PARAMETERS ==")

                    # Use wildcard query to get all parameter information
                    param_info = await query_osc_wildcard(
                        controller, "/device/param/**"
                    )

                    # Process and display parameters
                    if param_info:
                        # Group parameters by their index
                        params_by_index = {}
                        for addr, value in param_info.items():
                            # Extract parameter index from address
                            parts = addr.split("/")
                            if (
                                len(parts) >= 4
                                and parts[1] == "device"
                                and parts[2] == "param"
                            ):
                                try:
                                    param_index = int(parts[3])
                                    field = "/".join(parts[4:])

                                    # Initialize dict for this parameter if needed
                                    if param_index not in params_by_index:
                                        params_by_index[param_index] = {}

                                    params_by_index[param_index][field] = value
                                except (ValueError, IndexError):
                                    # Skip addresses we can't parse
                                    continue

                        # Display parameters in order
                        for idx in sorted(params_by_index.keys()):
                            param_data = params_by_index[idx]

                            # Skip if exists is False or not present
                            if not param_data.get("exists", False):
                                continue

                            # Get key fields
                            name = param_data.get("name", f"Parameter {idx}")
                            value = param_data.get("value", "N/A")
                            value_str = param_data.get("value/str", "")

                            # Format display
                            display_value = f"{value}"
                            if value_str:
                                display_value += f" ({value_str})"

                            print(f"  Parameter {idx}: {name} = {display_value}")
                    else:
                        print("  No parameters found")

                # ================ PART 2: Check Browser for Device ================
                # Use a simpler approach to find metadata about the device
                logger.info("\nSearching for device in browser...")

                # First try the "Result" tab which shows everything
                controller.client.browse_for_device("after")
                await asyncio.sleep(1.0)

                found_device = False
                exact_name_match = False
                result_details = {}

                # Check if browser is active
                browser_active = controller.server.get_message("/browser/isActive")
                if browser_active:
                    # First check which tab we're on
                    current_tab = controller.server.get_message("/browser/tab")
                    logger.info(f"Current browser tab: {current_tab}")

                    # Try to navigate to the "Result" tab which has everything
                    for _ in range(8):  # Try up to 8 times
                        if current_tab in ["Result", "Everything"]:
                            break
                        controller.client.navigate_browser_tab("+")  # Move to next tab
                        await asyncio.sleep(0.5)
                        current_tab = controller.server.get_message("/browser/tab")
                        logger.info(f"Navigated to tab: {current_tab}")

                    # Check each page of results
                    max_pages = 3  # Check up to 3 pages for the device
                    for page in range(max_pages):
                        if page > 0:
                            # Move to next page
                            logger.info(f"Checking page {page+1}...")
                            controller.client.select_next_browser_result_page()
                            await asyncio.sleep(1.0)

                        # Refresh browser state
                        controller.client.refresh()
                        await asyncio.sleep(0.5)

                        # Check each result on this page
                        logger.info(f"Scanning results on page {page+1}...")
                        for i in range(1, 17):  # Up to 16 results per page
                            result_exists = controller.server.get_message(
                                f"/browser/result/{i}/exists"
                            )
                            if not result_exists:
                                continue

                            result_name = controller.server.get_message(
                                f"/browser/result/{i}/name"
                            )
                            if not result_name:
                                continue

                            # Check if this is our device
                            name_match = False

                            # First check for exact match (case insensitive)
                            if result_name.lower() == args.address.lower():
                                logger.info(f"✅ Found exact match: {result_name}")
                                name_match = True
                                exact_name_match = True
                            # Then check for partial match
                            elif args.address.lower() in result_name.lower():
                                logger.info(f"Found partial match: {result_name}")
                                name_match = True

                            if name_match:
                                found_device = True

                                # Remember basic details
                                result_details["name"] = result_name
                                result_details["page"] = page + 1
                                result_details["index"] = i

                                # Select this item to get filter information
                                logger.info("Selecting result to get more details...")
                                controller.client.send(f"/browser/result/{i}/select", 1)
                                await asyncio.sleep(0.5)

                                # First get basic result fields that are safe to query
                                for field in ["exists", "isSelected"]:
                                    value = controller.server.get_message(
                                        f"/browser/result/{i}/{field}"
                                    )
                                    if value is not None:
                                        result_details[field] = value

                                # Get filter metadata which is more reliable
                                for filter_idx in range(1, 7):  # Up to 6 filters
                                    filter_exists = controller.server.get_message(
                                        f"/browser/filter/{filter_idx}/exists"
                                    )
                                    if not filter_exists:
                                        continue

                                    filter_name = controller.server.get_message(
                                        f"/browser/filter/{filter_idx}/name"
                                    )
                                    if not filter_name:
                                        continue

                                    # Different ways to get selected filter values
                                    selected_item = None

                                    # Try the selectedItemName first
                                    selected_item_name = controller.server.get_message(
                                        f"/browser/filter/{filter_idx}/selectedItemName"
                                    )
                                    if (
                                        selected_item_name
                                        and not selected_item_name.startswith(
                                            f"Any {filter_name}"
                                        )
                                    ):
                                        selected_item = selected_item_name

                                    if selected_item:
                                        if filter_name.lower() in [
                                            "category",
                                            "device type",
                                            "type",
                                            "creator",
                                        ]:
                                            result_details[filter_name] = selected_item

                                # Exit early if we found an exact match
                                if exact_name_match:
                                    break

                        # Exit page loop if we found an exact match
                        if exact_name_match:
                            break

                    # Display the metadata we found
                    if found_device:
                        logger.info("\n== DEVICE METADATA ==")
                        # Print all the metadata we collected in a consistent order
                        ordered_fields = [
                            "name",
                            "page",
                            "index",
                            "Category",
                            "Creator",
                            "Device Type",
                            "Type",
                        ]

                        # Print ordered fields first if they exist
                        for field in ordered_fields:
                            if field in result_details:
                                print(f"  {field}: {result_details[field]}")

                        # Print any other fields we found
                        for field, value in result_details.items():
                            if field not in ordered_fields:
                                print(f"  {field}: {value}")
                    else:
                        logger.info("No matching devices found in browser results")

                    # Close the browser when we're done
                    controller.client.cancel_browser()
                    await asyncio.sleep(0.5)

                # ================ PART 3: Check for Parameters ================
                # Look for existing device parameters if we haven't found parameters yet
                if not current_device_match and not (browser_active and found_device):
                    await asyncio.sleep(0.5)
                    logger.info("\nChecking for matching device parameters...")

                    # Try to find parameters with matching names
                    found_params = []
                    for i in range(1, 9):  # Check up to 8 params
                        param_name = controller.server.get_message(
                            f"/device/param/{i}/name"
                        )
                        if param_name and args.address.lower() in param_name.lower():
                            param_value = controller.server.get_message(
                                f"/device/param/{i}/value"
                            )
                            param_value_str = controller.server.get_message(
                                f"/device/param/{i}/value/str"
                            )
                            found_params.append(
                                (i, param_name, param_value, param_value_str)
                            )

                    if found_params:
                        logger.info(f"Found {len(found_params)} matching parameters:")
                        for i, name, value, value_str in found_params:
                            display_value = f"{value}"
                            if value_str:
                                display_value += f" ({value_str})"
                            print(f"  Parameter {i}: {name} = {display_value}")

                # ================ PART 4: Find Related OSC Addresses ================
                # If we haven't found anything specific yet, try a wildcard search
                if (
                    not current_device_match
                    and not (browser_active and found_device)
                    and not found_params
                ):
                    logger.info(
                        "\nRunning wildcard search for related OSC addresses..."
                    )
                    matches = await query_osc_wildcard(
                        controller, f"/**/*{args.address}*"
                    )

                    if matches:
                        logger.info(
                            f"Found {len(matches)} addresses containing '{args.address}':"
                        )
                        for addr in sorted(matches.keys()):
                            value = matches[addr]
                            print(f"  {addr} = {value}")
                    else:
                        logger.info(f"No addresses containing '{args.address}' found")

            # Check if the address contains wildcards
            elif "*" in args.address or "?" in args.address:
                # Handle wildcard query
                logger.info(f"Querying OSC addresses matching: {args.address}")

                # Update pattern with ** if prefix mode was requested (backward compatibility)
                pattern = args.address
                if args.prefix and "**" not in pattern:
                    # Convert old prefix mode to new ** syntax
                    if pattern.endswith("/*"):
                        pattern = pattern[:-2] + "/**"
                    else:
                        pattern = pattern + "/**"
                    logger.info(
                        f"Prefix mode enabled: Converted to recursive pattern: {pattern}"
                    )

                # Log wildcard explanation
                if "**" in pattern:
                    logger.info(
                        "Using recursive wildcard (**) - matching across multiple path segments"
                    )
                elif "*" in pattern:
                    logger.info(
                        "Using single-level wildcard (*) - matching within single path segments"
                    )

                if "?" in pattern:
                    logger.info(
                        "Using character wildcard (?) - matching single characters within path segments"
                    )

                # Execute the query
                matches = await query_osc_wildcard(controller, pattern)

                if matches:
                    logger.info(f"\nFound {len(matches)} matching addresses:")
                    for addr, value in sorted(matches.items()):
                        logger.info(f"{addr}: {value}")
                else:
                    logger.warning(f"No matches found for pattern: {pattern}")
            else:
                # Handle single address query
                result = await query_osc_address(controller, args.address, args.value)
                if result is not None:
                    logger.info(f"Result: {result}")
                else:
                    logger.warning(f"No result received for {args.address}")

                # Show all received messages if requested
                if args.all_messages:
                    logger.info("\nAll received messages:")
                    for addr, value in sorted(
                        controller.server.received_messages.items()
                    ):
                        logger.info(f"{addr}: {value}")

    finally:
        # Clean up
        if controller:
            controller.stop()


def main():
    """Parse command line arguments and run the tool."""
    parser = argparse.ArgumentParser(
        description="Query OSC addresses in Bitwig Studio",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Wildcard Pattern Matching:
  This tool supports two types of wildcards for flexible address matching:

  * (single asterisk): Matches exactly one path segment
    Example: "/browser/filter/*/name" matches "/browser/filter/0/name" but not "/browser/filter/0/item/1/name"

  ** (double asterisk): Matches any number of path segments (recursive)
    Example: "/browser/**/name" matches both "/browser/filter/0/name" and "/browser/filter/0/item/1/name"

  ? (question mark): Matches a single character within a path segment
    Example: "/track/?/volume" matches "/track/1/volume" but not "/track/10/volume"

Examples:
  # Query a specific OSC address
  python osc_query.py "/browser/tab/name/0"

  # Send a command with a value
  python osc_query.py "/browser/isActive" 1

  # Match one specific path level with *
  python osc_query.py "/browser/filter/*/name"

  # Match multiple path levels with **
  python osc_query.py "/browser/**/name"

  # Query track volume for all tracks
  python osc_query.py "/track/*/volume"

  # Query all result properties for result 0
  python osc_query.py "/browser/result/0/**"

  # Use --prefix flag (now converted to ** internally)
  python osc_query.py --prefix "/browser/filter/0"  # equivalent to "/browser/filter/0/**"

  # Show common OSC addresses
  python osc_query.py --list

  # Show common OSC addresses with all messages
  python osc_query.py --list --all-messages

  # Scan for active browser endpoints
  python osc_query.py --scan-browser

  # Scan browser with full message output
  python osc_query.py --scan-browser --all-messages
""",
    )

    # Add arguments
    parser.add_argument(
        "address",
        nargs="?",
        help="The OSC address to query (e.g., /browser/tab/name/0)",
    )

    parser.add_argument(
        "value", nargs="?", help="Optional value to send with the address"
    )

    parser.add_argument("--list", action="store_true", help="Show common OSC addresses")

    parser.add_argument(
        "--scan-browser", action="store_true", help="Scan for active browser endpoints"
    )

    parser.add_argument(
        "--all-messages",
        action="store_true",
        help="Show all received messages, not just the relevant ones",
    )

    parser.add_argument(
        "--prefix",
        action="store_true",
        help="Use prefix matching mode (automatically adds '**' to pattern for backward compatibility)",
    )

    # Parse arguments
    args = parser.parse_args()

    # Make sure we have required arguments
    if not (args.address or args.list or args.scan_browser):
        parser.print_help()
        sys.exit(1)

    # Run the async function
    asyncio.run(run_osc_query(args))


if __name__ == "__main__":
    main()
