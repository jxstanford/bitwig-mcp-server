"""
Integration tests for the Bitwig MCP Server app module.

These tests verify the actual integration between the MCP server
and Bitwig Studio through OSC protocol.
"""

import asyncio
import logging
from typing import AsyncGenerator, Tuple

import pytest
import pytest_asyncio
from mcp.client.session import ClientSession
from mcp.shared.memory import create_client_server_memory_streams

from bitwig_mcp_server.mcp.server import BitwigMCPServer
from tests.conftest import skip_if_bitwig_not_running

# Set up logging
logger = logging.getLogger(__name__)

# Skip tests if Bitwig is not running
pytestmark = skip_if_bitwig_not_running


@pytest_asyncio.fixture
async def server_client() -> (
    AsyncGenerator[Tuple[BitwigMCPServer, ClientSession], None]
):
    """Create a BitwigMCPServer and connected MCP client session."""
    # Create server with different ports to avoid conflicts
    from bitwig_mcp_server.settings import Settings

    test_settings = Settings(bitwig_receive_port=9001, bitwig_send_port=8001)
    server = BitwigMCPServer(test_settings)

    # Create memory streams for client-server communication
    async with create_client_server_memory_streams() as streams:
        client_streams, server_streams = streams
        client_read, client_write = client_streams
        server_read, server_write = server_streams

        # Create client session
        client = ClientSession(client_read, client_write)

        # Start server in background
        server_task = asyncio.create_task(
            server.mcp_server.run(
                server_read,
                server_write,
                server.mcp_server.create_initialization_options(),
            )
        )

        # Start the OSC controller
        await server.start()

        try:
            # Initialize client
            await client.initialize()

            # Yield server and client to the test
            yield server, client
        finally:
            # Clean up
            server_task.cancel()
            try:
                await asyncio.wait_for(server_task, timeout=1.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass

            await server.stop()


class TestBitwigMCPServerIntegration:
    """Integration tests for BitwigMCPServer."""

    @pytest.mark.asyncio
    async def test_list_tools(self, server_client):
        """Test listing available tools."""
        _, client = server_client

        # List tools
        tools_result = await client.list_tools()
        tools = tools_result.tools if hasattr(tools_result, "tools") else []

        # Check that we have tools available
        assert tools, "No tools returned from server"

        # Log available tools
        tool_names = [tool.name for tool in tools]
        logger.info(f"Available tools: {tool_names}")

        # Verify some essential tools are present
        assert any(name for name in tool_names if "play" in name), "Missing play tool"
        assert any(name for name in tool_names if "tempo" in name), "Missing tempo tool"

    @pytest.mark.asyncio
    async def test_transport_control(self, server_client):
        """Test controlling transport via tools."""
        server, client = server_client

        # Find play tool
        tools_result = await client.list_tools()
        tools = tools_result.tools if hasattr(tools_result, "tools") else []
        play_tools = [tool for tool in tools if "play" in tool.name]

        assert play_tools, "No play tool found"
        play_tool = play_tools[0]

        # Get initial play state
        initial_state = bool(server.controller.server.get_message("/play"))
        logger.info(f"Initial play state: {initial_state}")

        # Toggle playback
        result = await client.call_tool(play_tool.name)

        # Wait briefly for state to propagate
        await asyncio.sleep(0.5)

        # Check that state changed (or at least we got a response)
        assert result is not None, "No response from play tool"

        # Toggle back to original state
        await client.call_tool(play_tool.name)

    @pytest.mark.asyncio
    async def test_tempo_control(self, server_client):
        """Test setting tempo via tools."""
        server, client = server_client

        # Find tempo tool
        tools_result = await client.list_tools()
        tools = tools_result.tools if hasattr(tools_result, "tools") else []
        tempo_tools = [tool for tool in tools if "tempo" in tool.name]

        assert tempo_tools, "No tempo tool found"
        tempo_tool = tempo_tools[0]

        # Get current tempo
        server.controller.client.refresh()
        await asyncio.sleep(0.5)  # Wait for response

        initial_tempo = server.controller.server.get_message("/tempo/raw")
        test_tempo = 120.0  # Use a standard value if we can't get current tempo

        if initial_tempo is not None:
            # Calculate a new tempo value that's different from current
            test_tempo = (
                initial_tempo + 10 if initial_tempo < 150 else initial_tempo - 10
            )

        # Set the tempo
        result = await client.call_tool(tempo_tool.name, {"bpm": test_tempo})

        # Verify we got a response
        assert result is not None, "No response from tempo tool"

        # Reset tempo to original value if we know it
        if initial_tempo is not None:
            await client.call_tool(tempo_tool.name, {"bpm": initial_tempo})

    @pytest.mark.asyncio
    async def test_list_resources(self, server_client):
        """Test listing available resources."""
        _, client = server_client

        # List resources
        resources_result = await client.list_resources()
        resources = (
            resources_result.resources if hasattr(resources_result, "resources") else []
        )

        # Check that we have resources available
        assert resources, "No resources returned from server"

        # Verify some essential resources are present
        resource_uris = [resource.uri for resource in resources]
        assert any(
            uri for uri in resource_uris if "transport" in uri
        ), "Missing transport resource"

    @pytest.mark.asyncio
    async def test_read_resource(self, server_client):
        """Test reading resources."""
        _, client = server_client

        # List resources to find valid ones
        resources_result = await client.list_resources()
        resources = (
            resources_result.resources if hasattr(resources_result, "resources") else []
        )

        # Find a transport resource
        transport_resources = [
            resource for resource in resources if "transport" in resource.uri
        ]
        assert transport_resources, "No transport resource found"

        # Read the transport resource
        resource_uri = transport_resources[0].uri
        logger.info(f"Reading resource: {resource_uri}")

        resource_result = await client.read_resource(resource_uri)

        # Verify we got a response
        assert resource_result is not None, "No content returned from resource"
        assert hasattr(resource_result, "contents"), "Resource result missing contents"
