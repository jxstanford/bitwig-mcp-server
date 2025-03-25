"""
Integration tests for the Bitwig MCP Server.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from mcp.types import TextContent

from bitwig_mcp_server.mcp.server import BitwigMCPServer
from bitwig_mcp_server.settings import Settings


@pytest.fixture
def mock_osc_controller():
    """Mock BitwigOSCController for integration tests."""
    controller = MagicMock()
    controller.ready = True
    controller.start = MagicMock()
    controller.stop = MagicMock()
    controller.client = MagicMock()
    controller.server = MagicMock()

    # Simulate OSC server responses
    controller.server.get_message = MagicMock(
        side_effect=lambda path: {
            "/play": True,
            "/tempo/raw": 120.0,
            "/track/1/name": "Audio Track",
            "/track/1/volume": 64,
            "/device/exists": True,
            "/device/name": "EQ+",
        }.get(path)
    )

    return controller


@pytest.fixture
def bitwig_mcp_server(mock_osc_controller):
    """BitwigMCPServer with mocked OSC controller for integration tests."""
    with patch(
        "bitwig_mcp_server.mcp.server.BitwigOSCController",
        return_value=mock_osc_controller,
    ):
        server = BitwigMCPServer(Settings())
        return server


@pytest.mark.asyncio
async def test_full_server_lifecycle(bitwig_mcp_server, mock_osc_controller):
    """Test full server lifecycle including start, operations, and stop."""
    # Start the server
    await bitwig_mcp_server.start()
    mock_osc_controller.start.assert_called_once()

    # Wait a bit to simulate running
    await asyncio.sleep(0.1)

    # Stop the server
    await bitwig_mcp_server.stop()
    mock_osc_controller.stop.assert_called_once()


@pytest.mark.asyncio
async def test_tool_resource_integration(bitwig_mcp_server, mock_osc_controller):
    """Test tools and resources working together with the OSC controller."""
    # Mock the transport_play tool execution
    mock_execute_tool = AsyncMock(
        return_value=[TextContent(type="text", text="Transport play/pause toggled")]
    )

    # Start the server
    await bitwig_mcp_server.start()

    # Test calling a tool
    with patch("bitwig_mcp_server.mcp.tools.execute_tool", mock_execute_tool):
        result = await bitwig_mcp_server.call_tool("transport_play", {})
        assert result[0].text == "Transport play/pause toggled"

    # Test reading a resource
    with patch(
        "bitwig_mcp_server.mcp.resources.read_resource",
        AsyncMock(return_value="Transport State:\nPlaying: True\nTempo: 120.0 BPM"),
    ):
        resource_content = await bitwig_mcp_server.read_resource("bitwig://transport")
        assert "Transport State:" in resource_content
        assert "Playing: True" in resource_content
        assert "Tempo: 120.0 BPM" in resource_content

    # Stop the server
    await bitwig_mcp_server.stop()


@pytest.mark.asyncio
async def test_error_handling_integration(bitwig_mcp_server):
    """Test error handling across components."""
    # Start with a controller that fails to become ready
    with patch.object(bitwig_mcp_server.controller, "ready", False):
        with pytest.raises(
            RuntimeError, match="Bitwig OSC controller failed to initialize"
        ):
            await bitwig_mcp_server.start()

    # Reset controller ready state
    bitwig_mcp_server.controller.ready = True
    await bitwig_mcp_server.start()

    # Test error handling when calling a non-existent tool
    with patch(
        "bitwig_mcp_server.mcp.tools.execute_tool",
        AsyncMock(side_effect=ValueError("Unknown tool")),
    ):
        result = await bitwig_mcp_server.call_tool("non_existent_tool", {})
        assert "Error: Unknown tool" in result[0].text

    # Test error handling when reading a non-existent resource
    with patch(
        "bitwig_mcp_server.mcp.resources.read_resource",
        AsyncMock(side_effect=ValueError("Unknown resource")),
    ):
        with pytest.raises(
            ValueError, match="Failed to read resource test://invalid: Unknown resource"
        ):
            await bitwig_mcp_server.read_resource("test://invalid")

    # Stop the server
    await bitwig_mcp_server.stop()
