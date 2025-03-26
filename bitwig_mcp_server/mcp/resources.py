"""
Bitwig MCP Resources

This module provides MCP resources for Bitwig Studio integration.
"""

import asyncio
import logging
from typing import List

from mcp.types import Resource

from bitwig_mcp_server.osc.controller import BitwigOSCController

# Set up logging
logger = logging.getLogger(__name__)


def get_bitwig_resources() -> List[Resource]:
    """Get all available Bitwig resources

    Returns:
        List of Resource objects
    """
    return [
        Resource(
            uri="bitwig://transport",
            name="Transport Info",
            description="Current transport state (play/stop, tempo, etc.)",
            mimeType="text/plain",
        ),
        Resource(
            uri="bitwig://tracks",
            name="Tracks Info",
            description="Information about all tracks in the project",
            mimeType="text/plain",
        ),
        Resource(
            uri="bitwig://track/{index}",
            name="Track Details",
            description="Detailed information about a specific track",
            mimeType="text/plain",
        ),
        Resource(
            uri="bitwig://devices",
            name="Devices Info",
            description="Information about active devices and parameters",
            mimeType="text/plain",
        ),
        Resource(
            uri="bitwig://device/parameters",
            name="Device Parameters",
            description="Parameters for the selected device",
            mimeType="text/plain",
        ),
        Resource(
            uri="bitwig://device/{index}",
            name="Device Details",
            description="Detailed information about a specific device by index",
            mimeType="text/plain",
        ),
        Resource(
            uri="bitwig://device/{index}/parameters",
            name="Device Parameters by Index",
            description="Parameters for a specific device by index",
            mimeType="text/plain",
        ),
        Resource(
            uri="bitwig://device/siblings",
            name="Device Siblings",
            description="List of sibling devices in the current device chain",
            mimeType="text/plain",
        ),
        Resource(
            uri="bitwig://device/layers",
            name="Device Layers",
            description="List of layers in the current device",
            mimeType="text/plain",
        ),
        # Browser resources
        Resource(
            uri="bitwig://browser/isActive",
            name="Browser Active Status",
            description="Whether the browser is currently active",
            mimeType="text/plain",
        ),
        Resource(
            uri="bitwig://browser/tab",
            name="Browser Tab",
            description="The name of the selected browser tab",
            mimeType="text/plain",
        ),
        Resource(
            uri="bitwig://browser/filter/{filter_index}/wildcard",
            name="Browser Filter Wildcard",
            description="The name of the wildcard for a specific filter (1-6)",
            mimeType="text/plain",
        ),
        Resource(
            uri="bitwig://browser/filter/{filter_index}/exists",
            name="Browser Filter Exists",
            description="Whether a specific filter exists (1-6)",
            mimeType="text/plain",
        ),
        Resource(
            uri="bitwig://browser/filter/{filter_index}/name",
            name="Browser Filter Name",
            description="The name of a specific filter (1-6)",
            mimeType="text/plain",
        ),
        Resource(
            uri="bitwig://browser/filter/{filter_index}/item/{item_index}/exists",
            name="Browser Filter Item Exists",
            description="Whether a specific filter item exists (filter 1-6, item 1-16)",
            mimeType="text/plain",
        ),
        Resource(
            uri="bitwig://browser/filter/{filter_index}/item/{item_index}/name",
            name="Browser Filter Item Name",
            description="The name of a specific filter item (filter 1-6, item 1-16)",
            mimeType="text/plain",
        ),
        Resource(
            uri="bitwig://browser/filter/{filter_index}/item/{item_index}/hits",
            name="Browser Filter Item Hits",
            description="The number of result hits for a specific filter item (filter 1-6, item 1-16)",
            mimeType="text/plain",
        ),
        Resource(
            uri="bitwig://browser/filter/{filter_index}/item/{item_index}/isSelected",
            name="Browser Filter Item Selected",
            description="Whether a specific filter item is selected (filter 1-6, item 1-16)",
            mimeType="text/plain",
        ),
        Resource(
            uri="bitwig://browser/result/{result_index}/exists",
            name="Browser Result Exists",
            description="Whether a specific result item exists (1-16)",
            mimeType="text/plain",
        ),
        Resource(
            uri="bitwig://browser/result/{result_index}/name",
            name="Browser Result Name",
            description="The name of a specific result item (1-16)",
            mimeType="text/plain",
        ),
        Resource(
            uri="bitwig://browser/result/{result_index}/isSelected",
            name="Browser Result Selected",
            description="Whether a specific result item is selected (1-16)",
            mimeType="text/plain",
        ),
        # Aggregate resources for convenience
        Resource(
            uri="bitwig://browser/filters",
            name="Browser Filters",
            description="Information about all browser filters",
            mimeType="text/plain",
        ),
        Resource(
            uri="bitwig://browser/filter/{filter_index}/items",
            name="Browser Filter Items",
            description="Information about all items in a specific filter (1-6)",
            mimeType="text/plain",
        ),
        Resource(
            uri="bitwig://browser/results",
            name="Browser Results",
            description="Information about all browser results",
            mimeType="text/plain",
        ),
    ]


async def read_resource(controller: BitwigOSCController, uri: str) -> str:
    """Read a Bitwig resource

    Args:
        controller: BitwigOSCController instance
        uri: Resource URI to read

    Returns:
        Content of the resource as string

    Raises:
        ValueError: If resource URI is unknown
    """
    # Refresh state from Bitwig
    controller.client.refresh()
    await asyncio.sleep(0.5)  # Wait for responses

    try:
        if uri == "bitwig://transport":
            return _read_transport_resource(controller)

        elif uri == "bitwig://tracks":
            return _read_tracks_resource(controller)

        elif uri.startswith("bitwig://track/"):
            # Extract track index from URI
            try:
                track_index = int(uri.split("/")[-1])
                return _read_track_resource(controller, track_index)
            except (ValueError, IndexError):
                raise ValueError(f"Invalid track URI: {uri}")

        elif uri == "bitwig://devices":
            return _read_devices_resource(controller)

        elif uri == "bitwig://device/parameters":
            return _read_device_parameters_resource(controller)

        elif uri == "bitwig://device/siblings":
            return _read_device_siblings_resource(controller)

        elif uri == "bitwig://device/layers":
            return _read_device_layers_resource(controller)

        elif uri.startswith("bitwig://device/"):
            # Use proper URI parsing
            from urllib.parse import urlparse

            # Parse the URI
            parsed_uri = urlparse(uri)

            # Get the path component without leading slash
            path = parsed_uri.path.lstrip("/")
            path_parts = path.split("/")

            # Handle device/{index} (e.g., bitwig://device/1)
            if len(path_parts) == 1 and path_parts[0].isdigit():
                try:
                    device_index = int(path_parts[0])
                    return _read_device_resource_by_index(controller, device_index)
                except (ValueError, IndexError):
                    raise ValueError(f"Invalid device URI: {uri}")

            # Handle device/{index}/parameters (e.g., bitwig://device/1/parameters)
            elif (
                len(path_parts) == 2
                and path_parts[0].isdigit()
                and path_parts[1] == "parameters"
            ):
                try:
                    device_index = int(path_parts[0])
                    return _read_device_parameters_resource_by_index(
                        controller, device_index
                    )
                except (ValueError, IndexError):
                    raise ValueError(f"Invalid device parameters URI: {uri}")

        # Browser resources
        elif uri == "bitwig://browser/isActive":
            return _read_browser_active_resource(controller)

        elif uri == "bitwig://browser/tab":
            return _read_browser_tab_resource(controller)

        elif uri == "bitwig://browser/filters":
            return _read_browser_filters_resource(controller)

        elif uri.startswith("bitwig://browser/filter/"):
            # Parse the URI to get filter index
            parts = uri.split("/")

            # URI format: bitwig://browser/filter/{index}...
            if len(parts) < 5:
                raise ValueError(f"Invalid browser filter URI: {uri}")

            try:
                filter_index = int(parts[4])

                # Validate filter index
                if filter_index < 1 or filter_index > 6:
                    raise ValueError(
                        f"Filter index must be between 1 and 6: {filter_index}"
                    )

                # Handle different filter resource types
                if len(parts) == 5:  # bitwig://browser/filter/{index}
                    return _read_browser_filter_resource(controller, filter_index)

                elif len(parts) == 6 and parts[5] == "exists":
                    return _read_browser_filter_exists_resource(
                        controller, filter_index
                    )

                elif len(parts) == 6 and parts[5] == "name":
                    return _read_browser_filter_name_resource(controller, filter_index)

                elif len(parts) == 6 and parts[5] == "wildcard":
                    return _read_browser_filter_wildcard_resource(
                        controller, filter_index
                    )

                elif len(parts) == 6 and parts[5] == "items":
                    return _read_browser_filter_items_resource(controller, filter_index)

                elif len(parts) >= 7 and parts[5] == "item":
                    # URI format: bitwig://browser/filter/{filter_index}/item/{item_index}/...
                    try:
                        item_index = int(parts[6])

                        # Validate item index
                        if item_index < 1 or item_index > 16:
                            raise ValueError(
                                f"Item index must be between 1 and 16: {item_index}"
                            )

                        if (
                            len(parts) == 7
                        ):  # bitwig://browser/filter/{filter_index}/item/{item_index}
                            return _read_browser_filter_item_resource(
                                controller, filter_index, item_index
                            )

                        elif len(parts) == 8 and parts[7] == "exists":
                            return _read_browser_filter_item_exists_resource(
                                controller, filter_index, item_index
                            )

                        elif len(parts) == 8 and parts[7] == "name":
                            return _read_browser_filter_item_name_resource(
                                controller, filter_index, item_index
                            )

                        elif len(parts) == 8 and parts[7] == "hits":
                            return _read_browser_filter_item_hits_resource(
                                controller, filter_index, item_index
                            )

                        elif len(parts) == 8 and parts[7] == "isSelected":
                            return _read_browser_filter_item_selected_resource(
                                controller, filter_index, item_index
                            )

                    except (ValueError, IndexError):
                        raise ValueError(f"Invalid browser filter item URI: {uri}")

            except (ValueError, IndexError):
                raise ValueError(f"Invalid browser filter URI: {uri}")

        elif uri == "bitwig://browser/results":
            return _read_browser_results_resource(controller)

        elif uri.startswith("bitwig://browser/result/"):
            # Parse the URI to get result index
            parts = uri.split("/")

            # URI format: bitwig://browser/result/{index}...
            if len(parts) < 5:
                raise ValueError(f"Invalid browser result URI: {uri}")

            try:
                result_index = int(parts[4])

                # Validate result index
                if result_index < 1 or result_index > 16:
                    raise ValueError(
                        f"Result index must be between 1 and 16: {result_index}"
                    )

                if len(parts) == 5:  # bitwig://browser/result/{index}
                    return _read_browser_result_resource(controller, result_index)

                elif len(parts) == 6 and parts[5] == "exists":
                    return _read_browser_result_exists_resource(
                        controller, result_index
                    )

                elif len(parts) == 6 and parts[5] == "name":
                    return _read_browser_result_name_resource(controller, result_index)

                elif len(parts) == 6 and parts[5] == "isSelected":
                    return _read_browser_result_selected_resource(
                        controller, result_index
                    )

            except (ValueError, IndexError):
                raise ValueError(f"Invalid browser result URI: {uri}")

        else:
            raise ValueError(f"Unknown resource URI: {uri}")

    except Exception as e:
        logger.exception(f"Error reading resource {uri}: {e}")
        raise ValueError(f"Failed to read resource {uri}: {e}")


def _read_transport_resource(controller: BitwigOSCController) -> str:
    """Read transport resource

    Args:
        controller: BitwigOSCController instance

    Returns:
        Transport state information
    """
    play_state = controller.server.get_message("/play")
    tempo = controller.server.get_message("/tempo/raw")
    signature_num = controller.server.get_message("/signature/numerator")
    signature_denom = controller.server.get_message("/signature/denominator")

    result = ["Transport State:"]
    result.append(f"Playing: {bool(play_state)}")

    if tempo is not None:
        result.append(f"Tempo: {tempo} BPM")

    if signature_num is not None and signature_denom is not None:
        result.append(f"Time Signature: {signature_num}/{signature_denom}")

    return "\n".join(result)


def _read_tracks_resource(controller: BitwigOSCController) -> str:
    """Read tracks resource

    Args:
        controller: BitwigOSCController instance

    Returns:
        Information about all tracks
    """
    tracks_info = []

    # Attempt to get information for up to 10 tracks
    for i in range(1, 11):
        name = controller.server.get_message(f"/track/{i}/name")

        # If we have a name, consider the track valid
        if name:
            volume = controller.server.get_message(f"/track/{i}/volume")
            pan = controller.server.get_message(f"/track/{i}/pan")
            mute = controller.server.get_message(f"/track/{i}/mute")
            solo = controller.server.get_message(f"/track/{i}/solo")
            armed = controller.server.get_message(f"/track/{i}/recarm")

            track_info = [f"Track {i}: {name}"]
            if volume is not None:
                track_info.append(f"  Volume: {volume}")
            if pan is not None:
                track_info.append(f"  Pan: {pan}")
            if mute is not None:
                track_info.append(f"  Mute: {bool(mute)}")
            if solo is not None:
                track_info.append(f"  Solo: {bool(solo)}")
            if armed is not None:
                track_info.append(f"  Record Armed: {bool(armed)}")

            tracks_info.append("\n".join(track_info))

    if tracks_info:
        return "Tracks:\n\n" + "\n\n".join(tracks_info)
    else:
        return "No tracks found"


def _read_track_resource(controller: BitwigOSCController, track_index: int) -> str:
    """Read specific track resource

    Args:
        controller: BitwigOSCController instance
        track_index: Index of the track to read

    Returns:
        Detailed information about the track

    Raises:
        ValueError: If track is not found
    """
    name = controller.server.get_message(f"/track/{track_index}/name")
    if not name:
        raise ValueError(f"Track {track_index} not found")

    result = [f"Track: {name}", f"Index: {track_index}"]

    # Additional track properties
    properties = {
        "type": "Type",
        "volume": "Volume",
        "pan": "Pan",
        "mute": "Mute",
        "solo": "Solo",
        "recarm": "Record Armed",
        "color": "Color",
        "sends": "Send Count",
    }

    for prop_key, prop_name in properties.items():
        value = controller.server.get_message(f"/track/{track_index}/{prop_key}")
        if value is not None:
            if prop_key in ["mute", "solo", "recarm"]:
                value = bool(value)
            result.append(f"{prop_name}: {value}")

    return "\n".join(result)


def _read_devices_resource(controller: BitwigOSCController) -> str:
    """Read devices resource

    Args:
        controller: BitwigOSCController instance

    Returns:
        Information about active devices
    """
    devices_info = []

    # Check if a device is selected/active
    device_exists = controller.server.get_message("/device/exists")

    if device_exists:
        device_name = controller.server.get_message("/device/name")
        devices_info.append(f"Active Device: {device_name}")

        # Get device chain info if available
        chain_size = controller.server.get_message("/device/chain/size")
        if chain_size:
            devices_info.append(f"Device Chain Size: {chain_size}")

            for i in range(1, int(chain_size) + 1):
                device_chain_name = controller.server.get_message(
                    f"/device/chain/{i}/name"
                )
                if device_chain_name:
                    devices_info.append(f"  {i}: {device_chain_name}")

    if devices_info:
        return "\n".join(devices_info)
    else:
        return "No active device found"


def _read_device_parameters_resource(controller: BitwigOSCController) -> str:
    """Read device parameters resource

    Args:
        controller: BitwigOSCController instance

    Returns:
        Information about parameters for the selected device
    """
    params_info = []

    # Check if a device is selected/active
    device_exists = controller.server.get_message("/device/exists")

    if device_exists:
        device_name = controller.server.get_message("/device/name")
        params_info.append(f"Device: {device_name}")
        params_info.append("Parameters:")

        # Get information for up to 8 parameters
        for i in range(1, 9):
            param_exists = controller.server.get_message(f"/device/param/{i}/exists")
            if param_exists:
                param_name = controller.server.get_message(f"/device/param/{i}/name")
                param_value = controller.server.get_message(f"/device/param/{i}/value")
                value_str = controller.server.get_message(
                    f"/device/param/{i}/value/str"
                )

                param_info = f"  {i}: {param_name} = {param_value}"
                if value_str:
                    param_info += f" ({value_str})"

                params_info.append(param_info)

    if params_info:
        return "\n".join(params_info)
    else:
        return "No device parameters found"


def _read_device_siblings_resource(controller: BitwigOSCController) -> str:
    """Read device siblings resource

    Args:
        controller: BitwigOSCController instance

    Returns:
        Information about sibling devices in the current chain
    """
    siblings_info = []

    # Check if a device is selected/active
    device_exists = controller.server.get_message("/device/exists")

    if device_exists:
        device_name = controller.server.get_message("/device/name")
        siblings_info.append(f"Current Device: {device_name}")
        siblings_info.append("Sibling Devices:")

        # Get device chain size
        chain_size = controller.server.get_message("/device/chain/size")
        if chain_size:
            chain_size = int(chain_size)
            # Maximum of 8 siblings can be accessed via OSC
            max_siblings = min(chain_size, 8)

            for i in range(1, max_siblings + 1):
                sibling_name = controller.server.get_message(
                    f"/device/sibling/{i}/name"
                )
                sibling_exists = controller.server.get_message(
                    f"/device/sibling/{i}/exists"
                )
                sibling_bypassed = controller.server.get_message(
                    f"/device/sibling/{i}/bypass"
                )

                if sibling_exists:
                    sibling_info = [f"  {i}: {sibling_name}"]

                    # If we have additional information about the sibling
                    if sibling_bypassed is not None:
                        sibling_info.append(f"    Bypassed: {bool(sibling_bypassed)}")

                    siblings_info.append("\n".join(sibling_info))

    if len(siblings_info) > 2:  # More than just the headers
        return "\n".join(siblings_info)
    else:
        return "No sibling devices found"


def _read_device_layers_resource(controller: BitwigOSCController) -> str:
    """Read device layers resource

    Args:
        controller: BitwigOSCController instance

    Returns:
        Information about layers in the current device
    """
    layers_info = []

    # Check if a device is selected/active
    device_exists = controller.server.get_message("/device/exists")

    if device_exists:
        device_name = controller.server.get_message("/device/name")
        layers_info.append(f"Device: {device_name}")
        layers_info.append("Layers:")

        # Get device layers count
        layers_count = controller.server.get_message("/device/layer/exists")

        if layers_count:
            # Maximum of 8 layers can be accessed via OSC
            for i in range(1, 9):
                layer_exists = controller.server.get_message(
                    f"/device/layer/{i}/exists"
                )
                if layer_exists:
                    layer_name = controller.server.get_message(
                        f"/device/layer/{i}/name"
                    )
                    layer_info = f"  {i}: {layer_name}"
                    layers_info.append(layer_info)

                    # Get chain size within this layer if available
                    layer_chain_size = controller.server.get_message(
                        f"/device/layer/{i}/chain/size"
                    )
                    if layer_chain_size:
                        layers_info.append(f"    Contains {layer_chain_size} devices")

    if len(layers_info) > 2:  # More than just the headers
        return "\n".join(layers_info)
    else:
        return "No device layers found or device does not support layers"


def _read_device_resource_by_index(
    controller: BitwigOSCController, device_index: int
) -> str:
    """Read specific device resource by index

    Args:
        controller: BitwigOSCController instance
        device_index: Index of the device to read

    Returns:
        Detailed information about the device

    Raises:
        ValueError: If device is not found
    """
    # Select the device by index
    controller.client.select_device_by_index(device_index)

    # Wait for Bitwig to process the device selection
    # Bitwig can take significant time to respond, especially when busy
    import time

    time.sleep(2.0)  # Initial 2 second delay to allow Bitwig to process the selection

    # Try up to 3 times with longer delays to get device state
    for attempt in range(3):
        # Check if device selection succeeded
        device_exists = controller.server.get_message("/device/exists")
        if device_exists:
            break
        # Give Bitwig significantly more time to respond
        time.sleep(1.0)  # Additional 1 second per attempt, up to 5 seconds total
    if not device_exists:
        raise ValueError(f"Device {device_index} not found")

    device_name = controller.server.get_message("/device/name")
    result = [f"Device: {device_name}", f"Index: {device_index}"]

    # Additional device properties
    properties = {
        "bypass": "Bypassed",
        "chain/size": "Chain Size",
        "preset/name": "Preset",
        "category": "Category",
    }

    for prop_key, prop_name in properties.items():
        value = controller.server.get_message(f"/device/{prop_key}")
        if value is not None:
            if prop_key == "bypass":
                value = bool(value)
            result.append(f"{prop_name}: {value}")

    return "\n".join(result)


def _read_device_parameters_resource_by_index(
    controller: BitwigOSCController, device_index: int
) -> str:
    """Read parameters for a specific device by index

    Args:
        controller: BitwigOSCController instance
        device_index: Index of the device to read parameters for

    Returns:
        Information about parameters for the specified device

    Raises:
        ValueError: If device is not found
    """
    # Select the device by index
    controller.client.select_device_by_index(device_index)

    # Wait for Bitwig to process the device selection
    # Bitwig can take significant time to respond, especially when busy
    import time

    time.sleep(2.0)  # Initial 2 second delay to allow Bitwig to process the selection

    # Try up to 3 times with longer delays to get device state
    for attempt in range(3):
        # Check if device selection succeeded
        device_exists = controller.server.get_message("/device/exists")
        if device_exists:
            break
        # Give Bitwig significantly more time to respond
        time.sleep(1.0)  # Additional 1 second per attempt, up to 5 seconds total
    if not device_exists:
        raise ValueError(f"Device {device_index} not found")

    return _read_device_parameters_resource(controller)


# Browser resource reading functions


def _read_browser_active_resource(controller: BitwigOSCController) -> str:
    """Read browser active status

    Args:
        controller: BitwigOSCController instance

    Returns:
        Browser active status
    """
    is_active = controller.server.get_message("/browser/isActive")
    return f"Browser Active: {bool(is_active)}"


def _read_browser_tab_resource(controller: BitwigOSCController) -> str:
    """Read browser tab

    Args:
        controller: BitwigOSCController instance

    Returns:
        Browser tab information
    """
    tab = controller.server.get_message("/browser/tab")
    return f"Browser Tab: {tab}"


def _read_browser_filters_resource(controller: BitwigOSCController) -> str:
    """Read browser filters information

    Args:
        controller: BitwigOSCController instance

    Returns:
        Information about all browser filters
    """
    result = ["Browser Filters:"]

    # Check up to 6 filters
    for i in range(1, 7):
        filter_exists = controller.server.get_message(f"/browser/filter/{i}/exists")
        if filter_exists:
            filter_name = controller.server.get_message(f"/browser/filter/{i}/name")
            filter_wildcard = controller.server.get_message(
                f"/browser/filter/{i}/wildcard"
            )

            filter_info = [f"Filter {i}: {filter_name}"]
            if filter_wildcard:
                filter_info.append(f"  Wildcard: {filter_wildcard}")

            # Add filter items
            has_items = False
            for j in range(1, 17):
                item_exists = controller.server.get_message(
                    f"/browser/filter/{i}/item/{j}/exists"
                )
                if item_exists:
                    if not has_items:
                        filter_info.append("  Items:")
                        has_items = True

                    item_name = controller.server.get_message(
                        f"/browser/filter/{i}/item/{j}/name"
                    )
                    item_selected = controller.server.get_message(
                        f"/browser/filter/{i}/item/{j}/isSelected"
                    )
                    item_hits = controller.server.get_message(
                        f"/browser/filter/{i}/item/{j}/hits"
                    )

                    item_info = f"    {j}: {item_name}"
                    if item_selected:
                        item_info += " [Selected]"
                    if item_hits is not None:
                        item_info += f" ({item_hits} hits)"

                    filter_info.append(item_info)

            result.append("\n".join(filter_info))

    if len(result) == 1:  # Only the header
        return "No browser filters available"

    return "\n\n".join(result)


def _read_browser_filter_resource(
    controller: BitwigOSCController, filter_index: int
) -> str:
    """Read browser filter information

    Args:
        controller: BitwigOSCController instance
        filter_index: Index of the filter (1-6)

    Returns:
        Information about the specified filter

    Raises:
        ValueError: If filter does not exist
    """
    filter_exists = controller.server.get_message(
        f"/browser/filter/{filter_index}/exists"
    )
    if not filter_exists:
        raise ValueError(f"Filter {filter_index} does not exist")

    filter_name = controller.server.get_message(f"/browser/filter/{filter_index}/name")
    filter_wildcard = controller.server.get_message(
        f"/browser/filter/{filter_index}/wildcard"
    )

    result = [f"Filter {filter_index}: {filter_name}"]
    if filter_wildcard:
        result.append(f"Wildcard: {filter_wildcard}")

    # Add filter items
    has_items = False
    for i in range(1, 17):
        item_exists = controller.server.get_message(
            f"/browser/filter/{filter_index}/item/{i}/exists"
        )
        if item_exists:
            if not has_items:
                result.append("Items:")
                has_items = True

            item_name = controller.server.get_message(
                f"/browser/filter/{filter_index}/item/{i}/name"
            )
            item_selected = controller.server.get_message(
                f"/browser/filter/{filter_index}/item/{i}/isSelected"
            )
            item_hits = controller.server.get_message(
                f"/browser/filter/{filter_index}/item/{i}/hits"
            )

            item_info = f"  {i}: {item_name}"
            if item_selected:
                item_info += " [Selected]"
            if item_hits is not None:
                item_info += f" ({item_hits} hits)"

            result.append(item_info)

    return "\n".join(result)


def _read_browser_filter_exists_resource(
    controller: BitwigOSCController, filter_index: int
) -> str:
    """Read browser filter exists status

    Args:
        controller: BitwigOSCController instance
        filter_index: Index of the filter (1-6)

    Returns:
        Whether the filter exists
    """
    filter_exists = controller.server.get_message(
        f"/browser/filter/{filter_index}/exists"
    )
    return f"Filter {filter_index} Exists: {bool(filter_exists)}"


def _read_browser_filter_name_resource(
    controller: BitwigOSCController, filter_index: int
) -> str:
    """Read browser filter name

    Args:
        controller: BitwigOSCController instance
        filter_index: Index of the filter (1-6)

    Returns:
        Name of the filter

    Raises:
        ValueError: If filter does not exist
    """
    filter_exists = controller.server.get_message(
        f"/browser/filter/{filter_index}/exists"
    )
    if not filter_exists:
        raise ValueError(f"Filter {filter_index} does not exist")

    filter_name = controller.server.get_message(f"/browser/filter/{filter_index}/name")
    return f"Filter {filter_index} Name: {filter_name}"


def _read_browser_filter_wildcard_resource(
    controller: BitwigOSCController, filter_index: int
) -> str:
    """Read browser filter wildcard

    Args:
        controller: BitwigOSCController instance
        filter_index: Index of the filter (1-6)

    Returns:
        Wildcard of the filter

    Raises:
        ValueError: If filter does not exist
    """
    filter_exists = controller.server.get_message(
        f"/browser/filter/{filter_index}/exists"
    )
    if not filter_exists:
        raise ValueError(f"Filter {filter_index} does not exist")

    filter_wildcard = controller.server.get_message(
        f"/browser/filter/{filter_index}/wildcard"
    )
    return f"Filter {filter_index} Wildcard: {filter_wildcard}"


def _read_browser_filter_items_resource(
    controller: BitwigOSCController, filter_index: int
) -> str:
    """Read browser filter items

    Args:
        controller: BitwigOSCController instance
        filter_index: Index of the filter (1-6)

    Returns:
        Information about items in the filter

    Raises:
        ValueError: If filter does not exist
    """
    filter_exists = controller.server.get_message(
        f"/browser/filter/{filter_index}/exists"
    )
    if not filter_exists:
        raise ValueError(f"Filter {filter_index} does not exist")

    filter_name = controller.server.get_message(f"/browser/filter/{filter_index}/name")
    result = [f"Items for Filter {filter_index}: {filter_name}"]

    # Check for items
    has_items = False
    for i in range(1, 17):
        item_exists = controller.server.get_message(
            f"/browser/filter/{filter_index}/item/{i}/exists"
        )
        if item_exists:
            has_items = True
            item_name = controller.server.get_message(
                f"/browser/filter/{filter_index}/item/{i}/name"
            )
            item_selected = controller.server.get_message(
                f"/browser/filter/{filter_index}/item/{i}/isSelected"
            )
            item_hits = controller.server.get_message(
                f"/browser/filter/{filter_index}/item/{i}/hits"
            )

            item_info = f"{i}: {item_name}"
            if item_selected:
                item_info += " [Selected]"
            if item_hits is not None:
                item_info += f" ({item_hits} hits)"

            result.append(item_info)

    if not has_items:
        result.append("No items found")

    return "\n".join(result)


def _read_browser_filter_item_resource(
    controller: BitwigOSCController, filter_index: int, item_index: int
) -> str:
    """Read browser filter item information

    Args:
        controller: BitwigOSCController instance
        filter_index: Index of the filter (1-6)
        item_index: Index of the item (1-16)

    Returns:
        Information about the filter item

    Raises:
        ValueError: If filter or item does not exist
    """
    filter_exists = controller.server.get_message(
        f"/browser/filter/{filter_index}/exists"
    )
    if not filter_exists:
        raise ValueError(f"Filter {filter_index} does not exist")

    item_exists = controller.server.get_message(
        f"/browser/filter/{filter_index}/item/{item_index}/exists"
    )
    if not item_exists:
        raise ValueError(f"Item {item_index} in filter {filter_index} does not exist")

    item_name = controller.server.get_message(
        f"/browser/filter/{filter_index}/item/{item_index}/name"
    )
    item_selected = controller.server.get_message(
        f"/browser/filter/{filter_index}/item/{item_index}/isSelected"
    )
    item_hits = controller.server.get_message(
        f"/browser/filter/{filter_index}/item/{item_index}/hits"
    )

    result = [f"Filter {filter_index}, Item {item_index}: {item_name}"]
    result.append(f"Selected: {bool(item_selected)}")
    if item_hits is not None:
        result.append(f"Hits: {item_hits}")

    return "\n".join(result)


def _read_browser_filter_item_exists_resource(
    controller: BitwigOSCController, filter_index: int, item_index: int
) -> str:
    """Read browser filter item exists status

    Args:
        controller: BitwigOSCController instance
        filter_index: Index of the filter (1-6)
        item_index: Index of the item (1-16)

    Returns:
        Whether the filter item exists

    Raises:
        ValueError: If filter does not exist
    """
    filter_exists = controller.server.get_message(
        f"/browser/filter/{filter_index}/exists"
    )
    if not filter_exists:
        raise ValueError(f"Filter {filter_index} does not exist")

    item_exists = controller.server.get_message(
        f"/browser/filter/{filter_index}/item/{item_index}/exists"
    )
    return f"Filter {filter_index}, Item {item_index} Exists: {bool(item_exists)}"


def _read_browser_filter_item_name_resource(
    controller: BitwigOSCController, filter_index: int, item_index: int
) -> str:
    """Read browser filter item name

    Args:
        controller: BitwigOSCController instance
        filter_index: Index of the filter (1-6)
        item_index: Index of the item (1-16)

    Returns:
        Name of the filter item

    Raises:
        ValueError: If filter or item does not exist
    """
    filter_exists = controller.server.get_message(
        f"/browser/filter/{filter_index}/exists"
    )
    if not filter_exists:
        raise ValueError(f"Filter {filter_index} does not exist")

    item_exists = controller.server.get_message(
        f"/browser/filter/{filter_index}/item/{item_index}/exists"
    )
    if not item_exists:
        raise ValueError(f"Item {item_index} in filter {filter_index} does not exist")

    item_name = controller.server.get_message(
        f"/browser/filter/{filter_index}/item/{item_index}/name"
    )
    return f"Filter {filter_index}, Item {item_index} Name: {item_name}"


def _read_browser_filter_item_hits_resource(
    controller: BitwigOSCController, filter_index: int, item_index: int
) -> str:
    """Read browser filter item hits

    Args:
        controller: BitwigOSCController instance
        filter_index: Index of the filter (1-6)
        item_index: Index of the item (1-16)

    Returns:
        Number of hits for the filter item

    Raises:
        ValueError: If filter or item does not exist
    """
    filter_exists = controller.server.get_message(
        f"/browser/filter/{filter_index}/exists"
    )
    if not filter_exists:
        raise ValueError(f"Filter {filter_index} does not exist")

    item_exists = controller.server.get_message(
        f"/browser/filter/{filter_index}/item/{item_index}/exists"
    )
    if not item_exists:
        raise ValueError(f"Item {item_index} in filter {filter_index} does not exist")

    item_hits = controller.server.get_message(
        f"/browser/filter/{filter_index}/item/{item_index}/hits"
    )
    return f"Filter {filter_index}, Item {item_index} Hits: {item_hits}"


def _read_browser_filter_item_selected_resource(
    controller: BitwigOSCController, filter_index: int, item_index: int
) -> str:
    """Read browser filter item selected status

    Args:
        controller: BitwigOSCController instance
        filter_index: Index of the filter (1-6)
        item_index: Index of the item (1-16)

    Returns:
        Whether the filter item is selected

    Raises:
        ValueError: If filter or item does not exist
    """
    filter_exists = controller.server.get_message(
        f"/browser/filter/{filter_index}/exists"
    )
    if not filter_exists:
        raise ValueError(f"Filter {filter_index} does not exist")

    item_exists = controller.server.get_message(
        f"/browser/filter/{filter_index}/item/{item_index}/exists"
    )
    if not item_exists:
        raise ValueError(f"Item {item_index} in filter {filter_index} does not exist")

    item_selected = controller.server.get_message(
        f"/browser/filter/{filter_index}/item/{item_index}/isSelected"
    )
    return f"Filter {filter_index}, Item {item_index} Selected: {bool(item_selected)}"


def _read_browser_results_resource(controller: BitwigOSCController) -> str:
    """Read browser results information

    Args:
        controller: BitwigOSCController instance

    Returns:
        Information about browser results
    """
    result = ["Browser Results:"]

    # Check for results
    has_results = False
    for i in range(1, 17):
        result_exists = controller.server.get_message(f"/browser/result/{i}/exists")
        if result_exists:
            has_results = True
            result_name = controller.server.get_message(f"/browser/result/{i}/name")
            result_selected = controller.server.get_message(
                f"/browser/result/{i}/isSelected"
            )

            result_info = f"{i}: {result_name}"
            if result_selected:
                result_info += " [Selected]"

            result.append(result_info)

    if not has_results:
        result.append("No results found")

    return "\n".join(result)


def _read_browser_result_resource(
    controller: BitwigOSCController, result_index: int
) -> str:
    """Read browser result information

    Args:
        controller: BitwigOSCController instance
        result_index: Index of the result (1-16)

    Returns:
        Information about the browser result

    Raises:
        ValueError: If result does not exist
    """
    result_exists = controller.server.get_message(
        f"/browser/result/{result_index}/exists"
    )
    if not result_exists:
        raise ValueError(f"Result {result_index} does not exist")

    result_name = controller.server.get_message(f"/browser/result/{result_index}/name")
    result_selected = controller.server.get_message(
        f"/browser/result/{result_index}/isSelected"
    )

    result = [f"Result {result_index}: {result_name}"]
    result.append(f"Selected: {bool(result_selected)}")

    return "\n".join(result)


def _read_browser_result_exists_resource(
    controller: BitwigOSCController, result_index: int
) -> str:
    """Read browser result exists status

    Args:
        controller: BitwigOSCController instance
        result_index: Index of the result (1-16)

    Returns:
        Whether the browser result exists
    """
    result_exists = controller.server.get_message(
        f"/browser/result/{result_index}/exists"
    )
    return f"Result {result_index} Exists: {bool(result_exists)}"


def _read_browser_result_name_resource(
    controller: BitwigOSCController, result_index: int
) -> str:
    """Read browser result name

    Args:
        controller: BitwigOSCController instance
        result_index: Index of the result (1-16)

    Returns:
        Name of the browser result

    Raises:
        ValueError: If result does not exist
    """
    result_exists = controller.server.get_message(
        f"/browser/result/{result_index}/exists"
    )
    if not result_exists:
        raise ValueError(f"Result {result_index} does not exist")

    result_name = controller.server.get_message(f"/browser/result/{result_index}/name")
    return f"Result {result_index} Name: {result_name}"


def _read_browser_result_selected_resource(
    controller: BitwigOSCController, result_index: int
) -> str:
    """Read browser result selected status

    Args:
        controller: BitwigOSCController instance
        result_index: Index of the result (1-16)

    Returns:
        Whether the browser result is selected

    Raises:
        ValueError: If result does not exist
    """
    result_exists = controller.server.get_message(
        f"/browser/result/{result_index}/exists"
    )
    if not result_exists:
        raise ValueError(f"Result {result_index} does not exist")

    result_selected = controller.server.get_message(
        f"/browser/result/{result_index}/isSelected"
    )
    return f"Result {result_index} Selected: {bool(result_selected)}"
