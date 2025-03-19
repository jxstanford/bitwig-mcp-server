"""
Bitwig MCP Client

This module provides a simple client for the Bitwig MCP Server.
"""

import asyncio
import logging
from typing import Any, Optional

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.types import AnyUrl

logger = logging.getLogger(__name__)


class BitwigMCPClient:
    """Client for the Bitwig MCP Server."""

    def __init__(self, command: Optional[str] = None, args: Optional[list[str]] = None):
        """Initialize a Bitwig MCP Client.

        Args:
            command: Command to run the server (default: 'python -m bitwig_mcp_server')
            args: Additional arguments for the server
        """
        self.command = command or "python"
        self.args = args or ["-m", "bitwig_mcp_server"]
        self.session = None

    async def connect(self) -> None:
        """Connect to the Bitwig MCP Server."""
        params = StdioServerParameters(command=self.command, args=self.args)
        self.streams = await stdio_client(params).__aenter__()
        self.session = await ClientSession(*self.streams).__aenter__()
        await self.session.initialize()
        logger.info("Connected to Bitwig MCP Server")

    async def disconnect(self) -> None:
        """Disconnect from the Bitwig MCP Server."""
        if self.session:
            await self.session.__aexit__(None, None, None)
            self.session = None
        if hasattr(self, "streams"):
            await self.streams[0].__aexit__(None, None, None)
            await self.streams[1].__aexit__(None, None, None)
        logger.info("Disconnected from Bitwig MCP Server")

    async def __aenter__(self) -> "BitwigMCPClient":
        """Enter async context manager."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit async context manager."""
        await self.disconnect()

    # Transport methods
    async def play(self) -> dict[str, Any]:
        """Start playback in Bitwig."""
        if not self.session:
            raise RuntimeError("Not connected to server")
        return await self.session.call_tool("play")

    async def stop(self) -> dict[str, Any]:
        """Stop playback in Bitwig."""
        if not self.session:
            raise RuntimeError("Not connected to server")
        return await self.session.call_tool("stop")

    async def set_tempo(self, bpm: float) -> dict[str, Any]:
        """Set the tempo in Bitwig.

        Args:
            bpm: Tempo in beats per minute (20-999)
        """
        if not self.session:
            raise RuntimeError("Not connected to server")
        return await self.session.call_tool("set_tempo", {"bpm": bpm})

    # Track methods
    async def set_track_volume(self, track_index: int, volume: float) -> dict[str, Any]:
        """Set track volume.

        Args:
            track_index: Track index (1-based)
            volume: Volume value (0-128, where 64 is 0dB)
        """
        if not self.session:
            raise RuntimeError("Not connected to server")
        return await self.session.call_tool(
            "set_track_volume", {"track_index": track_index, "volume": volume}
        )

    async def set_track_pan(self, track_index: int, pan: float) -> dict[str, Any]:
        """Set track pan position.

        Args:
            track_index: Track index (1-based)
            pan: Pan value (0-128, where 64 is center)
        """
        if not self.session:
            raise RuntimeError("Not connected to server")
        return await self.session.call_tool(
            "set_track_pan", {"track_index": track_index, "pan": pan}
        )

    async def set_track_mute(self, track_index: int, mute: bool) -> dict[str, Any]:
        """Mute or unmute a track.

        Args:
            track_index: Track index (1-based)
            mute: True to mute, False to unmute
        """
        if not self.session:
            raise RuntimeError("Not connected to server")
        return await self.session.call_tool(
            "set_track_mute", {"track_index": track_index, "mute": mute}
        )

    # Device methods
    async def set_device_parameter(
        self, param_index: int, value: float
    ) -> dict[str, Any]:
        """Set a device parameter value.

        Args:
            param_index: Parameter index (1-based)
            value: Parameter value (0-128)
        """
        if not self.session:
            raise RuntimeError("Not connected to server")
        return await self.session.call_tool(
            "set_device_parameter", {"param_index": param_index, "value": value}
        )

    # Resource methods
    async def get_project_info(self) -> str:
        """Get current project information."""
        if not self.session:
            raise RuntimeError("Not connected to server")
        result = await self.session.read_resource(AnyUrl("bitwig://project/info"))
        return result.contents[0].text

    async def get_track_list(self) -> str:
        """Get a list of all tracks in the project."""
        if not self.session:
            raise RuntimeError("Not connected to server")
        result = await self.session.read_resource(AnyUrl("bitwig://tracks"))
        return result.contents[0].text

    async def get_track_detail(self, track_index: int) -> str:
        """Get detailed information about a specific track.

        Args:
            track_index: Track index (1-based)
        """
        if not self.session:
            raise RuntimeError("Not connected to server")
        result = await self.session.read_resource(
            AnyUrl(f"bitwig://track/{track_index}")
        )
        return result.contents[0].text

    async def get_device_parameters(self) -> str:
        """Get parameters for the selected device."""
        if not self.session:
            raise RuntimeError("Not connected to server")
        result = await self.session.read_resource(AnyUrl("bitwig://device/parameters"))
        return result.contents[0].text


async def main():
    """Example client usage."""
    # Create client and connect
    async with BitwigMCPClient() as client:
        # Get project info
        print("Project info:")
        print(await client.get_project_info())
        print()

        # Get track list
        print("Track list:")
        print(await client.get_track_list())
        print()

        # Set tempo to 120 BPM
        print("Setting tempo to 120 BPM:")
        result = await client.set_tempo(120)
        print(result)
        print()

        # Play transport
        print("Starting playback:")
        result = await client.play()
        print(result)
        print()

        # Wait a bit
        print("Waiting 3 seconds...")
        await asyncio.sleep(3)

        # Stop transport
        print("Stopping playback:")
        result = await client.stop()
        print(result)
        print()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
