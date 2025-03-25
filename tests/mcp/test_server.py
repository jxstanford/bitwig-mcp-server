"""
Tests for the Bitwig MCP Server implementation.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from mcp.types import TextContent

from bitwig_mcp_server.mcp.server import BitwigMCPServer
from bitwig_mcp_server.settings import Settings


@pytest.fixture
def mock_osc_controller():
    """Mock BitwigOSCController."""
    controller = MagicMock()
    controller.ready = True
    controller.start = MagicMock()
    controller.stop = MagicMock()
    return controller


@pytest.fixture
def mock_mcp_server():
    """Mock MCP Server."""
    server = MagicMock()
    server.list_tools = MagicMock(return_value=lambda: None)
    server.call_tool = MagicMock(return_value=lambda: None)
    server.list_resources = MagicMock(return_value=lambda: None)
    server.read_resource = MagicMock(return_value=lambda: None)
    return server


@pytest.fixture
def bitwig_mcp_server(mock_osc_controller, mock_mcp_server):
    """BitwigMCPServer with mocked dependencies."""
    with (
        patch(
            "bitwig_mcp_server.mcp.server.BitwigOSCController",
            return_value=mock_osc_controller,
        ),
        patch("bitwig_mcp_server.mcp.server.MCPServer", return_value=mock_mcp_server),
    ):
        server = BitwigMCPServer(Settings())
        return server


@pytest.mark.asyncio
async def test_start_server(bitwig_mcp_server, mock_osc_controller):
    """Test starting the server."""
    await bitwig_mcp_server.start()
    mock_osc_controller.start.assert_called_once()


@pytest.mark.asyncio
async def test_stop_server(bitwig_mcp_server, mock_osc_controller):
    """Test stopping the server."""
    await bitwig_mcp_server.stop()
    mock_osc_controller.stop.assert_called_once()


@pytest.mark.asyncio
async def test_list_tools(bitwig_mcp_server):
    """Test list_tools method."""
    with patch(
        "bitwig_mcp_server.mcp.server.get_bitwig_tools", return_value=["tool1", "tool2"]
    ):
        tools = await bitwig_mcp_server.list_tools()
        assert tools == ["tool1", "tool2"]


@pytest.mark.asyncio
async def test_call_tool(bitwig_mcp_server, mock_osc_controller):
    """Test call_tool method."""
    mock_execute_tool = AsyncMock(
        return_value=[TextContent(type="text", text="Tool executed")]
    )

    with patch("bitwig_mcp_server.mcp.server.execute_tool", mock_execute_tool):
        result = await bitwig_mcp_server.call_tool("test_tool", {"arg": "value"})

        mock_execute_tool.assert_called_once_with(
            bitwig_mcp_server.controller, "test_tool", {"arg": "value"}
        )
        assert len(result) == 1
        assert result[0].type == "text"
        assert result[0].text == "Tool executed"


@pytest.mark.asyncio
async def test_call_tool_error(bitwig_mcp_server, mock_osc_controller):
    """Test call_tool method with error."""
    mock_execute_tool = AsyncMock(side_effect=ValueError("Tool error"))

    with patch("bitwig_mcp_server.mcp.server.execute_tool", mock_execute_tool):
        result = await bitwig_mcp_server.call_tool("test_tool", {"arg": "value"})

        assert len(result) == 1
        assert result[0].type == "text"
        assert "Error: Tool error" in result[0].text


@pytest.mark.asyncio
async def test_list_resources(bitwig_mcp_server):
    """Test list_resources method."""
    with patch(
        "bitwig_mcp_server.mcp.server.get_bitwig_resources",
        return_value=["resource1", "resource2"],
    ):
        resources = await bitwig_mcp_server.list_resources()
        assert resources == ["resource1", "resource2"]


@pytest.mark.asyncio
async def test_read_resource(bitwig_mcp_server, mock_osc_controller):
    """Test read_resource method."""
    mock_read_resource = AsyncMock(return_value="Resource content")

    with patch("bitwig_mcp_server.mcp.server.read_resource", mock_read_resource):
        result = await bitwig_mcp_server.read_resource("test://uri")

        mock_read_resource.assert_called_once_with(
            bitwig_mcp_server.controller, "test://uri"
        )
        assert result == "Resource content"


@pytest.mark.asyncio
async def test_read_resource_error(bitwig_mcp_server, mock_osc_controller):
    """Test read_resource method with error."""
    mock_read_resource = AsyncMock(side_effect=ValueError("Resource error"))

    with patch("bitwig_mcp_server.mcp.server.read_resource", mock_read_resource):
        with pytest.raises(ValueError) as excinfo:
            await bitwig_mcp_server.read_resource("test://uri")

        assert "Failed to read resource test://uri: Resource error" in str(
            excinfo.value
        )
