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
from bitwig_mcp_server.settings import Settings
from tests.conftest import skip_if_bitwig_not_running

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Skip tests if Bitwig is not running
pytestmark = skip_if_bitwig_not_running


@pytest_asyncio.fixture
async def server_client() -> (
    AsyncGenerator[Tuple[BitwigMCPServer, ClientSession], None]
):
    """Create a BitwigMCPServer and connected MCP client session."""
    # Create server with default ports (important: Bitwig needs to be configured to use these)
    test_settings = Settings()
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

        try:
            # Start the OSC controller
            logger.info("Starting MCP server and connecting to Bitwig...")
            await server.start()

            # Wait for server to be ready and verify connection
            wait_count = 0
            max_wait_count = 50  # 5 seconds
            while not server.controller.ready and wait_count < max_wait_count:
                await asyncio.sleep(0.1)
                wait_count += 1

            if not server.controller.ready:
                logger.error(
                    "Could not connect to Bitwig - server failed to initialize"
                )
                pytest.skip("Could not connect to Bitwig Studio")

            logger.info("MCP server connected to Bitwig successfully")

            # Make sure Bitwig is in a known state
            # Stop transport if playing
            play_state = server.controller.server.get_message("/play")
            if play_state:
                server.controller.client.stop()
                await asyncio.sleep(0.5)

            # Make sure browser is closed
            browser_active = server.controller.server.get_message("/browser/isActive")
            if browser_active:
                server.controller.client.cancel_browser()
                await asyncio.sleep(0.5)

            # Initialize client
            await client.initialize()

            # Yield server and client to the test
            yield server, client
        finally:
            # Clean up
            logger.info("Cleaning up after tests...")

            # Ensure Bitwig is left in a clean state
            if hasattr(server, "controller") and server.controller is not None:
                # Stop transport
                server.controller.client.stop()

                # Close browser if open
                browser_active = server.controller.server.get_message(
                    "/browser/isActive"
                )
                if browser_active:
                    server.controller.client.cancel_browser()
                    await asyncio.sleep(0.5)

            # Cancel MCP server task
            if server_task and not server_task.done():
                server_task.cancel()
                try:
                    await asyncio.wait_for(server_task, timeout=1.0)
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    pass

            # Stop server
            await server.stop()
            logger.info("Test cleanup completed")


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
        assert any(
            name for name in tool_names if "transport_play" == name
        ), "Missing transport_play tool"
        assert any(
            name for name in tool_names if "set_tempo" == name
        ), "Missing set_tempo tool"

    @pytest.mark.asyncio
    async def test_transport_control(self, server_client):
        """Test controlling transport via tools."""
        server, client = server_client

        # Find play tool
        tools_result = await client.list_tools()
        tools = tools_result.tools if hasattr(tools_result, "tools") else []
        play_tools = [tool for tool in tools if "transport_play" == tool.name]

        assert play_tools, "No transport_play tool found"
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
        await asyncio.sleep(0.5)  # Allow time for state to return to original

    @pytest.mark.asyncio
    async def test_tempo_control(self, server_client):
        """Test setting tempo via tools."""
        server, client = server_client

        # Find tempo tool
        tools_result = await client.list_tools()
        tools = tools_result.tools if hasattr(tools_result, "tools") else []
        tempo_tools = [tool for tool in tools if "set_tempo" == tool.name]

        assert tempo_tools, "No set_tempo tool found"
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

        # Wait briefly for change to take effect
        await asyncio.sleep(0.5)

        # Verify the tempo actually changed
        server.controller.client.refresh()
        await asyncio.sleep(0.5)
        updated_tempo = server.controller.server.get_message("/tempo/raw")

        # Check the tempo changed; allow for small rounding differences
        if updated_tempo is not None:
            logger.info(
                f"Changed tempo from {initial_tempo} to {updated_tempo} (target: {test_tempo})"
            )
            assert (
                abs(updated_tempo - test_tempo) < 0.1
            ), "Tempo didn't change as expected"

        # Reset tempo to original value if we know it
        if initial_tempo is not None:
            await client.call_tool(tempo_tool.name, {"bpm": initial_tempo})
            await asyncio.sleep(0.5)  # Allow time for restoration

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

        # Log some of the resources
        resource_uris = [str(resource.uri) for resource in resources]
        logger.info(f"Found {len(resource_uris)} resources")
        logger.info(f"Some resources: {resource_uris[:5]}...")

        # Verify some essential resources are present
        assert any(
            uri for uri in resource_uris if "transport" in uri
        ), "Missing transport resource"
        assert any(
            uri for uri in resource_uris if "tracks" in uri
        ), "Missing tracks resource"

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
            resource for resource in resources if "transport" in str(resource.uri)
        ]
        assert transport_resources, "No transport resource found"

        # Read the transport resource
        resource_uri = transport_resources[0].uri
        logger.info(f"Reading resource: {resource_uri}")

        resource_result = await client.read_resource(resource_uri)

        # Verify we got a response
        assert resource_result is not None, "No content returned from resource"
        assert hasattr(resource_result, "contents"), "Resource result missing contents"

        # Check content
        content = resource_result.contents
        logger.info(f"Resource content: {content[:100]}...")  # Log first 100 chars
        assert "Transport" in content, "Transport info not in resource content"
