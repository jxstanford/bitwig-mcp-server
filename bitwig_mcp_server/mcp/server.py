"""
Bitwig MCP Server

Implements the Model Context Protocol server for Bitwig Studio integration.
"""

import asyncio
import logging
from typing import Any

from mcp.server import Server
from mcp.types import Resource, TextContent, Tool

from bitwig_mcp_server.osc.controller import BitwigOSCController

# Set up logging
logger = logging.getLogger(__name__)


class BitwigMCPServer:
    """MCP server for Bitwig Studio integration"""

    def __init__(
        self, host: str = "127.0.0.1", send_port: int = 8000, receive_port: int = 9000
    ):
        """Initialize the Bitwig MCP server

        Args:
            host: Bitwig host IP address
            send_port: Port to send OSC messages to Bitwig
            receive_port: Port to receive OSC messages from Bitwig
        """
        # Create the MCP server
        self.mcp_server = Server("bitwig-mcp-server")

        # Create the Bitwig OSC controller
        self.controller = BitwigOSCController(host, send_port, receive_port)

        # Set up handlers
        self._setup_handlers()

    def _setup_handlers(self) -> None:
        """Set up MCP server handlers"""
        self.mcp_server.list_tools()(self.list_tools)
        self.mcp_server.call_tool()(self.call_tool)
        self.mcp_server.list_resources()(self.list_resources)
        self.mcp_server.read_resource()(self.read_resource)

    async def start(self) -> None:
        """Start the Bitwig MCP server"""
        # Start the OSC controller
        self.controller.start()

        # Wait for controller to be ready
        while not self.controller.ready:
            await asyncio.sleep(0.1)

        logger.info("Bitwig MCP Server started")

    async def stop(self) -> None:
        """Stop the Bitwig MCP server"""
        self.controller.stop()
        logger.info("Bitwig MCP Server stopped")

    async def list_tools(self) -> list[Tool]:
        """List available Bitwig tools"""
        return [
            Tool(
                name="transport_play",
                description="Toggle play/pause state of Bitwig",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
            Tool(
                name="set_tempo",
                description="Set the tempo of the Bitwig project",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "bpm": {
                            "type": "number",
                            "description": "Tempo in beats per minute (0-666)",
                        }
                    },
                    "required": ["bpm"],
                },
            ),
            Tool(
                name="set_track_volume",
                description="Set the volume of a track",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "track_index": {
                            "type": "integer",
                            "description": "Track index (1-based)",
                        },
                        "volume": {
                            "type": "number",
                            "description": "Volume value (0-128, where 64 is 0dB)",
                        },
                    },
                    "required": ["track_index", "volume"],
                },
            ),
            Tool(
                name="set_track_pan",
                description="Set the pan of a track",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "track_index": {
                            "type": "integer",
                            "description": "Track index (1-based)",
                        },
                        "pan": {
                            "type": "number",
                            "description": "Pan value (0-128, where 64 is center)",
                        },
                    },
                    "required": ["track_index", "pan"],
                },
            ),
            Tool(
                name="toggle_track_mute",
                description="Toggle mute state of a track",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "track_index": {
                            "type": "integer",
                            "description": "Track index (1-based)",
                        }
                    },
                    "required": ["track_index"],
                },
            ),
            Tool(
                name="set_device_parameter",
                description="Set value of a device parameter",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "param_index": {
                            "type": "integer",
                            "description": "Parameter index (1-based)",
                        },
                        "value": {
                            "type": "number",
                            "description": "Parameter value (0-128)",
                        },
                    },
                    "required": ["param_index", "value"],
                },
            ),
        ]

    async def call_tool(
        self, name: str, arguments: dict[str, Any]
    ) -> list[TextContent]:
        """Call a Bitwig tool"""
        try:
            if name == "transport_play":
                self.controller.client.play()
                return [TextContent(type="text", text="Transport play/pause toggled")]

            elif name == "set_tempo":
                bpm = arguments.get("bpm")
                if bpm is None:
                    raise ValueError("Missing required argument: bpm")

                self.controller.client.set_tempo(bpm)
                return [TextContent(type="text", text=f"Tempo set to {bpm} BPM")]

            elif name == "set_track_volume":
                track_index = arguments.get("track_index")
                volume = arguments.get("volume")
                if track_index is None or volume is None:
                    raise ValueError("Missing required arguments: track_index, volume")

                self.controller.client.set_track_volume(track_index, volume)
                return [
                    TextContent(
                        type="text", text=f"Track {track_index} volume set to {volume}"
                    )
                ]

            elif name == "set_track_pan":
                track_index = arguments.get("track_index")
                pan = arguments.get("pan")
                if track_index is None or pan is None:
                    raise ValueError("Missing required arguments: track_index, pan")

                self.controller.client.set_track_pan(track_index, pan)
                return [
                    TextContent(
                        type="text", text=f"Track {track_index} pan set to {pan}"
                    )
                ]

            elif name == "toggle_track_mute":
                track_index = arguments.get("track_index")
                if track_index is None:
                    raise ValueError("Missing required argument: track_index")

                self.controller.client.toggle_track_mute(track_index)
                return [
                    TextContent(type="text", text=f"Track {track_index} mute toggled")
                ]

            elif name == "set_device_parameter":
                param_index = arguments.get("param_index")
                value = arguments.get("value")
                if param_index is None or value is None:
                    raise ValueError("Missing required arguments: param_index, value")

                self.controller.client.set_device_parameter(param_index, value)
                return [
                    TextContent(
                        type="text",
                        text=f"Device parameter {param_index} set to {value}",
                    )
                ]

            else:
                raise ValueError(f"Unknown tool: {name}")

        except Exception as e:
            logger.exception(f"Error calling tool {name}: {e}")
            return [TextContent(type="text", text=f"Error: {e!s}")]

    async def list_resources(self) -> list[Resource]:
        """List available Bitwig resources"""
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
                uri="bitwig://devices",
                name="Devices Info",
                description="Information about active devices and parameters",
                mimeType="text/plain",
            ),
        ]

    async def read_resource(self, uri: str) -> str:
        """Read a Bitwig resource"""
        # Refresh state from Bitwig
        self.controller.client.refresh()
        await asyncio.sleep(0.5)  # Wait for responses

        if uri == "bitwig://transport":
            play_state = self.controller.server.get_message("/play")
            tempo = self.controller.server.get_message("/tempo/raw")
            return f"Transport State:\nPlaying: {bool(play_state)}\nTempo: {tempo} BPM"

        elif uri == "bitwig://tracks":
            tracks_info = []
            # Attempt to get information for up to 10 tracks
            for i in range(1, 11):
                name = self.controller.server.get_message(f"/track/{i}/name")
                volume = self.controller.server.get_message(f"/track/{i}/volume")
                pan = self.controller.server.get_message(f"/track/{i}/pan")
                mute = self.controller.server.get_message(f"/track/{i}/mute")
                solo = self.controller.server.get_message(f"/track/{i}/solo")

                # If we have a name, consider the track valid
                if name:
                    tracks_info.append(
                        f"Track {i}: {name}\n"
                        f"  Volume: {volume}\n"
                        f"  Pan: {pan}\n"
                        f"  Mute: {bool(mute)}\n"
                        f"  Solo: {bool(solo)}\n"
                    )

            return (
                "Tracks:\n" + "\n".join(tracks_info)
                if tracks_info
                else "No tracks found"
            )

        elif uri == "bitwig://devices":
            devices_info = []
            # Check if a device is selected/active
            device_exists = self.controller.server.get_message("/device/exists")

            if device_exists:
                device_name = self.controller.server.get_message("/device/name")
                devices_info.append(f"Active Device: {device_name}\nParameters:")

                # Get information for up to 8 parameters
                for i in range(1, 9):
                    param_exists = self.controller.server.get_message(
                        f"/device/param/{i}/exists"
                    )
                    if param_exists:
                        param_name = self.controller.server.get_message(
                            f"/device/param/{i}/name"
                        )
                        param_value = self.controller.server.get_message(
                            f"/device/param/{i}/value"
                        )
                        devices_info.append(f"  {i}: {param_name} = {param_value}")

            return "\n".join(devices_info) if devices_info else "No active device found"

        else:
            raise ValueError(f"Unknown resource URI: {uri}")


async def run_server():
    """Run the Bitwig MCP server"""
    server = BitwigMCPServer()
    await server.start()

    # Keep the server running
    try:
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        pass
    finally:
        await server.stop()


def main():
    """Main entry point"""
    try:
        asyncio.run(run_server())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")


if __name__ == "__main__":
    main()
