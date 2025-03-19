"""
Bitwig MCP Resources implementation.

This module defines the resources exposed via MCP for Bitwig Studio.
"""

import asyncio
import logging
from typing import List, Union

from mcp.server.lowlevel.helper_types import ReadResourceContents
from mcp.types import Resource
from pydantic import AnyUrl

from bitwig_mcp_server.osc.controller import BitwigOSCController

logger = logging.getLogger(__name__)


class BitwigResources:
    """Helper for Bitwig-specific MCP resources"""

    @staticmethod
    def get_resources() -> List[Resource]:
        """Get a list of all available Bitwig resources"""
        return [
            Resource(
                uri="bitwig://project/info",
                name="Project Info",
                description="Information about the current Bitwig project",
                mimeType="text/plain",
            ),
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
                description="Information about active devices",
                mimeType="text/plain",
            ),
            Resource(
                uri="bitwig://device/parameters",
                name="Device Parameters",
                description="Parameters for the selected device",
                mimeType="text/plain",
            ),
        ]

    @staticmethod
    async def read_resource(
        uri: Union[str, AnyUrl], controller: BitwigOSCController, refresh: bool = True
    ) -> List[ReadResourceContents]:
        """Read a specific Bitwig resource

        Args:
            uri: Resource URI to read
            controller: BitwigOSCController for OSC communication
            refresh: Whether to refresh state from Bitwig before reading

        Returns:
            Content of the resource as ReadResourceContents

        Raises:
            ValueError: If the resource URI is unknown
        """
        uri_str = str(uri)

        # Refresh state from Bitwig if needed
        if refresh:
            controller.client.refresh()
            await asyncio.sleep(0.5)  # Wait for responses

        if uri_str == "bitwig://project/info":
            project_name = controller.server.get_message("/project/name") or "Untitled"
            tempo = controller.server.get_message("/tempo/raw") or 120
            time_sig_num = controller.server.get_message("/signature/numerator") or 4
            time_sig_den = controller.server.get_message("/signature/denominator") or 4

            content = (
                f"Project: {project_name}\n"
                f"Tempo: {tempo} BPM\n"
                f"Time Signature: {time_sig_num}/{time_sig_den}"
            )
            return [ReadResourceContents(content=content, mime_type="text/plain")]

        elif uri_str == "bitwig://transport":
            play_state = controller.server.get_message("/play")
            tempo = controller.server.get_message("/tempo/raw")

            content = (
                f"Transport State:\nPlaying: {bool(play_state)}\nTempo: {tempo} BPM"
            )
            return [ReadResourceContents(content=content, mime_type="text/plain")]

        elif uri_str == "bitwig://tracks":
            tracks_info = []
            # Attempt to get information for up to 10 tracks
            for i in range(1, 11):
                name = controller.server.get_message(f"/track/{i}/name")
                volume = controller.server.get_message(f"/track/{i}/volume")
                pan = controller.server.get_message(f"/track/{i}/pan")
                mute = controller.server.get_message(f"/track/{i}/mute")
                solo = controller.server.get_message(f"/track/{i}/solo")

                # If we have a name, consider the track valid
                if name:
                    tracks_info.append(
                        f"Track {i}: {name}\n"
                        f"  Volume: {volume}\n"
                        f"  Pan: {pan}\n"
                        f"  Mute: {bool(mute)}\n"
                        f"  Solo: {bool(solo)}\n"
                    )

            content = (
                "Tracks:\n" + "\n".join(tracks_info)
                if tracks_info
                else "No tracks found"
            )
            return [ReadResourceContents(content=content, mime_type="text/plain")]

        elif uri_str.startswith("bitwig://track/"):
            try:
                track_index = int(uri_str.split("/")[-1])

                name = controller.server.get_message(f"/track/{track_index}/name")
                if not name:
                    return [
                        ReadResourceContents(
                            content=f"Track {track_index} not found",
                            mime_type="text/plain",
                        )
                    ]

                volume = controller.server.get_message(f"/track/{track_index}/volume")
                pan = controller.server.get_message(f"/track/{track_index}/pan")
                mute = controller.server.get_message(f"/track/{track_index}/mute")
                solo = controller.server.get_message(f"/track/{track_index}/solo")
                type = controller.server.get_message(f"/track/{track_index}/type")
                armed = controller.server.get_message(f"/track/{track_index}/recarm")

                content = (
                    f"Track: {name}\n"
                    f"Index: {track_index}\n"
                    f"Type: {type}\n"
                    f"Volume: {volume}\n"
                    f"Pan: {pan}\n"
                    f"Mute: {bool(mute)}\n"
                    f"Solo: {bool(solo)}\n"
                    f"Record Armed: {bool(armed)}\n"
                )
                return [ReadResourceContents(content=content, mime_type="text/plain")]
            except (ValueError, IndexError):
                return [
                    ReadResourceContents(
                        content="Invalid track URI", mime_type="text/plain"
                    )
                ]

        elif uri_str == "bitwig://devices":
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

            content = (
                "\n".join(devices_info) if devices_info else "No active device found"
            )
            return [ReadResourceContents(content=content, mime_type="text/plain")]

        elif uri_str == "bitwig://device/parameters":
            params_info = []
            # Check if a device is selected/active
            device_exists = controller.server.get_message("/device/exists")

            if device_exists:
                device_name = controller.server.get_message("/device/name")
                params_info.append(f"Device: {device_name}\nParameters:")

                # Get information for up to 8 parameters
                for i in range(1, 9):
                    param_exists = controller.server.get_message(
                        f"/device/param/{i}/exists"
                    )
                    if param_exists:
                        param_name = controller.server.get_message(
                            f"/device/param/{i}/name"
                        )
                        param_value = controller.server.get_message(
                            f"/device/param/{i}/value"
                        )
                        value_str = controller.server.get_message(
                            f"/device/param/{i}/value/str"
                        )

                        param_info = f"  {i}: {param_name} = {param_value}"
                        if value_str:
                            param_info += f" ({value_str})"

                        params_info.append(param_info)

            content = (
                "\n".join(params_info) if params_info else "No device parameters found"
            )
            return [ReadResourceContents(content=content, mime_type="text/plain")]

        else:
            raise ValueError(f"Unknown resource URI: {uri_str}")
