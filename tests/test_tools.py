"""
Tests for the Bitwig MCP Server tools module.
"""

from unittest.mock import MagicMock

import pytest

from bitwig_mcp_server.mcp.tools import execute_tool, get_bitwig_tools


def test_get_bitwig_tools():
    """Test that get_bitwig_tools returns the expected tools."""
    tools = get_bitwig_tools()

    # Check that we have the expected number of tools
    assert (
        len(tools) == 12
    )  # Transport, tempo, track controls (3), device params, device controls (6)

    # Check that the tools have the expected names
    tool_names = {tool.name for tool in tools}
    expected_names = {
        # Basic transport and track tools
        "transport_play",
        "set_tempo",
        "set_track_volume",
        "set_track_pan",
        "toggle_track_mute",
        "set_device_parameter",
        # New device tools
        "toggle_device_bypass",
        "select_device_sibling",
        "navigate_device",
        "enter_device_layer",
        "exit_device_layer",
        "toggle_device_window",
    }
    assert tool_names == expected_names

    # Check schema structure
    for tool in tools:
        assert hasattr(tool, "inputSchema")
        assert isinstance(tool.inputSchema, dict)
        assert "type" in tool.inputSchema
        assert tool.inputSchema["type"] == "object"


@pytest.mark.asyncio
async def test_execute_tool_transport_play():
    """Test execute_tool with transport_play tool."""
    # Create mock controller
    controller = MagicMock()
    controller.client = MagicMock()

    # Execute the tool
    result = await execute_tool(controller, "transport_play", {})

    # Check that the expected client method was called
    controller.client.play.assert_called_once()

    # Check the result
    assert len(result) == 1
    assert result[0].type == "text"
    assert "toggled" in result[0].text


@pytest.mark.asyncio
async def test_execute_tool_set_tempo():
    """Test execute_tool with set_tempo tool."""
    # Create mock controller
    controller = MagicMock()
    controller.client = MagicMock()

    # Execute the tool
    result = await execute_tool(controller, "set_tempo", {"bpm": 120})

    # Check that the expected client method was called with correct arguments
    controller.client.set_tempo.assert_called_once_with(120)

    # Check the result
    assert len(result) == 1
    assert result[0].type == "text"
    assert "120 BPM" in result[0].text


@pytest.mark.asyncio
async def test_execute_tool_set_tempo_missing_arg():
    """Test execute_tool with set_tempo tool and missing argument."""
    # Create mock controller
    controller = MagicMock()

    # Execute the tool with missing argument
    result = await execute_tool(controller, "set_tempo", {})

    # Check that the result indicates an error
    assert len(result) == 1
    assert result[0].type == "text"
    assert "Error" in result[0].text
    assert "Missing required argument: bpm" in result[0].text


@pytest.mark.asyncio
async def test_execute_tool_set_track_volume():
    """Test execute_tool with set_track_volume tool."""
    # Create mock controller
    controller = MagicMock()
    controller.client = MagicMock()

    # Execute the tool
    result = await execute_tool(
        controller, "set_track_volume", {"track_index": 1, "volume": 64}
    )

    # Check that the expected client method was called with correct arguments
    controller.client.set_track_volume.assert_called_once_with(1, 64)

    # Check the result
    assert len(result) == 1
    assert result[0].type == "text"
    assert "Track 1 volume set to 64" in result[0].text


@pytest.mark.asyncio
async def test_execute_tool_invalid_arguments():
    """Test execute_tool with invalid arguments."""
    # Create mock controller
    controller = MagicMock()

    # Test cases for various invalid arguments
    test_cases = [
        (
            "set_track_volume",
            {"track_index": "not-a-number", "volume": 64},
            "Invalid track_index",
        ),
        (
            "set_track_volume",
            {"track_index": 0, "volume": 64},
            "must be a positive integer",
        ),
        ("set_track_volume", {"track_index": 1, "volume": 200}, "Invalid volume"),
        ("set_device_parameter", {"param_index": 1, "value": -10}, "Invalid value"),
    ]

    for tool_name, args, expected_error in test_cases:
        result = await execute_tool(controller, tool_name, args)

        # Check that the result indicates the expected error
        assert len(result) == 1
        assert result[0].type == "text"
        assert "Error" in result[0].text
        assert expected_error in result[0].text


@pytest.mark.asyncio
async def test_execute_tool_unknown():
    """Test execute_tool with unknown tool."""
    # Create mock controller
    controller = MagicMock()

    # Execute with unknown tool name
    result = await execute_tool(controller, "unknown_tool", {})

    # Check that the result indicates the expected error
    assert len(result) == 1
    assert result[0].type == "text"
    assert "Error" in result[0].text
    assert "Unknown tool" in result[0].text


@pytest.mark.asyncio
async def test_execute_tool_toggle_device_bypass():
    """Test execute_tool with toggle_device_bypass tool."""
    # Create a mock controller
    controller = MagicMock()
    controller.client.toggle_device_bypass = MagicMock()

    # Execute the tool
    result = await execute_tool(controller, "toggle_device_bypass", {})

    # Check that the controller method was called
    controller.client.toggle_device_bypass.assert_called_once()

    # Check the result
    assert len(result) == 1
    assert result[0].type == "text"
    assert result[0].text == "Device bypass toggled"


@pytest.mark.asyncio
async def test_execute_tool_select_device_sibling():
    """Test execute_tool with select_device_sibling tool."""
    # Create a mock controller
    controller = MagicMock()
    controller.client.select_device_sibling = MagicMock()

    # Execute the tool
    result = await execute_tool(
        controller, "select_device_sibling", {"sibling_index": 3}
    )

    # Check that the controller method was called
    controller.client.select_device_sibling.assert_called_once_with(3)

    # Check the result
    assert len(result) == 1
    assert result[0].type == "text"
    assert result[0].text == "Selected sibling device 3"


@pytest.mark.asyncio
async def test_execute_tool_select_device_sibling_invalid_arg():
    """Test execute_tool with select_device_sibling tool and invalid arguments."""
    # Create a mock controller
    controller = MagicMock()

    # Test missing required argument
    result = await execute_tool(controller, "select_device_sibling", {})
    assert "Missing required argument" in result[0].text

    # Test invalid argument value
    result = await execute_tool(
        controller, "select_device_sibling", {"sibling_index": 0}
    )
    assert "Invalid sibling_index" in result[0].text

    result = await execute_tool(
        controller, "select_device_sibling", {"sibling_index": 9}
    )
    assert "Invalid sibling_index" in result[0].text


@pytest.mark.asyncio
async def test_execute_tool_navigate_device():
    """Test execute_tool with navigate_device tool."""
    # Create a mock controller
    controller = MagicMock()
    controller.client.navigate_device = MagicMock()

    # Execute the tool with "next" direction
    result = await execute_tool(controller, "navigate_device", {"direction": "next"})
    controller.client.navigate_device.assert_called_with("next")
    assert result[0].text == "Navigated to next device"

    # Execute the tool with "previous" direction
    result = await execute_tool(
        controller, "navigate_device", {"direction": "previous"}
    )
    controller.client.navigate_device.assert_called_with("previous")
    assert result[0].text == "Navigated to previous device"

    # Test invalid direction
    result = await execute_tool(controller, "navigate_device", {"direction": "invalid"})
    assert "Invalid direction" in result[0].text


@pytest.mark.asyncio
async def test_execute_tool_device_layer_operations():
    """Test execute_tool with device layer operations."""
    # Create a mock controller
    controller = MagicMock()
    controller.client.enter_device_layer = MagicMock()
    controller.client.exit_device_layer = MagicMock()

    # Test enter_device_layer
    result = await execute_tool(controller, "enter_device_layer", {"layer_index": 2})
    controller.client.enter_device_layer.assert_called_once_with(2)
    assert result[0].text == "Entered device layer 2"

    # Test exit_device_layer
    result = await execute_tool(controller, "exit_device_layer", {})
    controller.client.exit_device_layer.assert_called_once()
    assert result[0].text == "Exited device layer"

    # Test invalid layer index
    result = await execute_tool(controller, "enter_device_layer", {"layer_index": 0})
    assert "Invalid layer_index" in result[0].text


@pytest.mark.asyncio
async def test_execute_tool_toggle_device_window():
    """Test execute_tool with toggle_device_window tool."""
    # Create a mock controller
    controller = MagicMock()
    controller.client.toggle_device_window = MagicMock()

    # Execute the tool
    result = await execute_tool(controller, "toggle_device_window", {})

    # Check that the controller method was called
    controller.client.toggle_device_window.assert_called_once()

    # Check the result
    assert len(result) == 1
    assert result[0].type == "text"
    assert result[0].text == "Device window toggled"
