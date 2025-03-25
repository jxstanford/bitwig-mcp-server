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
