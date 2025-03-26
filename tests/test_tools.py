"""
Tests for the Bitwig MCP Server tools module.
"""

from unittest.mock import MagicMock

import pytest

from bitwig_mcp_server.mcp.tools import execute_tool, get_bitwig_tools


def test_get_bitwig_tools():
    """Test that get_bitwig_tools returns the expected tools."""
    tools = get_bitwig_tools()

    # Get all tool names
    tool_names = {tool.name for tool in tools}

    # Check that we have the expected transport and device tools
    expected_core_names = {
        # Basic transport and track tools
        "transport_play",
        "set_tempo",
        "set_track_volume",
        "set_track_pan",
        "toggle_track_mute",
        "set_device_parameter",
        # Device tools
        "toggle_device_bypass",
        "select_device_sibling",
        "navigate_device",
        "enter_device_layer",
        "exit_device_layer",
        "toggle_device_window",
    }

    # Check that we have browser-related tools
    expected_browser_names = {
        # Basic browser tools
        "browse_insert_device",
        "browse_device_presets",
        "commit_browser_selection",
        "cancel_browser",
        "navigate_browser_tab",
        "navigate_browser_filter",
        "reset_browser_filter",
        "navigate_browser_result",
        # Browser workflow tools
        "device_browser_workflow",
        "preset_browser_workflow",
        # Browser content tools
        "search_device_browser",
        "recommend_devices",
        "get_device_categories",
        "get_device_info",
    }

    # Verify that all expected tools are present
    for tool_name in expected_core_names:
        assert tool_name in tool_names, f"Missing core tool: {tool_name}"

    for tool_name in expected_browser_names:
        assert tool_name in tool_names, f"Missing browser tool: {tool_name}"

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


# Browser tool tests


@pytest.mark.asyncio
async def test_execute_tool_browse_insert_device():
    """Test execute_tool with browse_insert_device tool."""
    # Create a mock controller
    controller = MagicMock()
    controller.client.browse_for_device = MagicMock()

    # Test with default position ("after")
    result = await execute_tool(controller, "browse_insert_device", {})
    controller.client.browse_for_device.assert_called_with("after")
    assert "Browser opened to insert device after" in result[0].text

    # Test with explicit position
    controller.client.browse_for_device.reset_mock()
    result = await execute_tool(
        controller, "browse_insert_device", {"position": "before"}
    )
    controller.client.browse_for_device.assert_called_with("before")
    assert "Browser opened to insert device before" in result[0].text

    # Test with invalid position - error is caught and returned as a text result
    result = await execute_tool(
        controller, "browse_insert_device", {"position": "invalid"}
    )
    assert "Error" in result[0].text
    assert "Invalid position" in result[0].text


@pytest.mark.asyncio
async def test_execute_tool_browse_device_presets():
    """Test execute_tool with browse_device_presets tool."""
    # Create a mock controller
    controller = MagicMock()
    controller.client.browse_for_preset = MagicMock()

    # Execute the tool
    result = await execute_tool(controller, "browse_device_presets", {})

    # Check that the controller method was called
    controller.client.browse_for_preset.assert_called_once()

    # Check the result
    assert "Browser opened to browse device presets" in result[0].text


@pytest.mark.asyncio
async def test_execute_tool_browser_operations():
    """Test execute_tool with browser operation tools."""
    # Create a mock controller
    controller = MagicMock()

    # Test commit_browser_selection
    controller.client.commit_browser_selection = MagicMock()
    result = await execute_tool(controller, "commit_browser_selection", {})
    controller.client.commit_browser_selection.assert_called_once()
    assert "Browser selection committed" in result[0].text

    # Test cancel_browser
    controller.client.cancel_browser = MagicMock()
    result = await execute_tool(controller, "cancel_browser", {})
    controller.client.cancel_browser.assert_called_once()
    assert "Browser session canceled" in result[0].text


@pytest.mark.asyncio
async def test_execute_tool_navigate_browser_tab():
    """Test execute_tool with navigate_browser_tab tool."""
    # Create a mock controller
    controller = MagicMock()
    controller.client.navigate_browser_tab = MagicMock()

    # Test navigate next
    result = await execute_tool(
        controller, "navigate_browser_tab", {"direction": "next"}
    )
    controller.client.navigate_browser_tab.assert_called_with("+")
    assert "Navigated to next browser tab" in result[0].text

    # Test navigate previous
    controller.client.navigate_browser_tab.reset_mock()
    result = await execute_tool(
        controller, "navigate_browser_tab", {"direction": "previous"}
    )
    controller.client.navigate_browser_tab.assert_called_with("-")
    assert "Navigated to previous browser tab" in result[0].text

    # Test missing direction
    result = await execute_tool(controller, "navigate_browser_tab", {})
    assert "Error" in result[0].text
    assert "Missing required argument" in result[0].text

    # Test invalid direction
    result = await execute_tool(
        controller, "navigate_browser_tab", {"direction": "invalid"}
    )
    assert "Error" in result[0].text
    assert "Invalid direction" in result[0].text


@pytest.mark.asyncio
async def test_execute_tool_navigate_browser_filter():
    """Test execute_tool with navigate_browser_filter tool."""
    # Create a mock controller
    controller = MagicMock()
    controller.client.navigate_browser_filter = MagicMock()

    # Test navigate next
    result = await execute_tool(
        controller, "navigate_browser_filter", {"filter_index": 1, "direction": "next"}
    )
    controller.client.navigate_browser_filter.assert_called_with(1, "+")
    assert "Navigated to next option in filter 1" in result[0].text

    # Test navigate previous
    controller.client.navigate_browser_filter.reset_mock()
    result = await execute_tool(
        controller,
        "navigate_browser_filter",
        {"filter_index": 2, "direction": "previous"},
    )
    controller.client.navigate_browser_filter.assert_called_with(2, "-")
    assert "Navigated to previous option in filter 2" in result[0].text

    # Test missing arguments
    result = await execute_tool(controller, "navigate_browser_filter", {})
    assert "Error" in result[0].text
    assert "Missing required arguments" in result[0].text

    # Test invalid filter_index
    result = await execute_tool(
        controller, "navigate_browser_filter", {"filter_index": 0, "direction": "next"}
    )
    assert "Error" in result[0].text
    assert "Invalid filter_index" in result[0].text

    # Test invalid direction
    result = await execute_tool(
        controller,
        "navigate_browser_filter",
        {"filter_index": 1, "direction": "invalid"},
    )
    assert "Error" in result[0].text
    assert "Invalid direction" in result[0].text


@pytest.mark.asyncio
async def test_execute_tool_reset_browser_filter():
    """Test execute_tool with reset_browser_filter tool."""
    # Create a mock controller
    controller = MagicMock()
    controller.client.reset_browser_filter = MagicMock()

    # Test reset filter
    result = await execute_tool(controller, "reset_browser_filter", {"filter_index": 1})
    controller.client.reset_browser_filter.assert_called_with(1)
    assert "Reset filter 1" in result[0].text

    # Test missing filter_index
    result = await execute_tool(controller, "reset_browser_filter", {})
    assert "Error" in result[0].text
    assert "Missing required argument" in result[0].text

    # Test invalid filter_index
    result = await execute_tool(controller, "reset_browser_filter", {"filter_index": 0})
    assert "Error" in result[0].text
    assert "Invalid filter_index" in result[0].text


@pytest.mark.asyncio
async def test_execute_tool_navigate_browser_result():
    """Test execute_tool with navigate_browser_result tool."""
    # Create a mock controller
    controller = MagicMock()
    controller.client.navigate_browser_result = MagicMock()

    # Test navigate next
    result = await execute_tool(
        controller, "navigate_browser_result", {"direction": "next"}
    )
    controller.client.navigate_browser_result.assert_called_with("+")
    assert "Navigated to next browser result" in result[0].text

    # Test navigate previous
    controller.client.navigate_browser_result.reset_mock()
    result = await execute_tool(
        controller, "navigate_browser_result", {"direction": "previous"}
    )
    controller.client.navigate_browser_result.assert_called_with("-")
    assert "Navigated to previous browser result" in result[0].text

    # Test missing direction
    result = await execute_tool(controller, "navigate_browser_result", {})
    assert "Error" in result[0].text
    assert "Missing required argument" in result[0].text

    # Test invalid direction
    result = await execute_tool(
        controller, "navigate_browser_result", {"direction": "invalid"}
    )
    assert "Error" in result[0].text
    assert "Invalid direction" in result[0].text


@pytest.mark.asyncio
async def test_execute_tool_device_browser_workflow():
    """Test execute_tool with device_browser_workflow tool."""
    # Create a mock controller
    controller = MagicMock()
    controller.client.browse_for_device = MagicMock()
    controller.client.navigate_browser_tab = MagicMock()
    controller.client.navigate_browser_filter = MagicMock()
    controller.client.navigate_browser_result = MagicMock()
    controller.client.commit_browser_selection = MagicMock()

    # Test with basic parameters
    result = await execute_tool(
        controller,
        "device_browser_workflow",
        {
            "position": "after",
            "num_tab_navigations": 2,
            "filter_navigations": [
                {"filter_index": 1, "steps": 3},
                {"filter_index": 2, "steps": -1},
            ],
            "result_navigations": 4,
        },
    )

    # Check that all required methods were called
    controller.client.browse_for_device.assert_called_with("after")
    assert controller.client.navigate_browser_tab.call_count == 2
    assert controller.client.navigate_browser_filter.call_count == 4  # 3 + 1
    assert controller.client.navigate_browser_result.call_count == 4
    controller.client.commit_browser_selection.assert_called_once()

    # Check the result
    assert "Device browser workflow completed successfully" in result[0].text

    # Test with invalid parameters
    result = await execute_tool(
        controller, "device_browser_workflow", {"position": "invalid"}
    )
    assert "Error" in result[0].text
    assert "Invalid position" in result[0].text

    result = await execute_tool(
        controller, "device_browser_workflow", {"num_tab_navigations": "invalid"}
    )
    assert "Error" in result[0].text
    assert "Invalid num_tab_navigations" in result[0].text

    result = await execute_tool(
        controller,
        "device_browser_workflow",
        {
            "filter_navigations": [
                {"filter_index": 0, "steps": 1}  # Invalid filter index
            ]
        },
    )
    assert "Error" in result[0].text
    assert "Invalid filter_index" in result[0].text

    result = await execute_tool(
        controller,
        "device_browser_workflow",
        {
            "filter_navigations": [
                {"filter_index": 1, "steps": "invalid"}  # Invalid steps
            ]
        },
    )
    assert "Error" in result[0].text
    assert "Invalid steps" in result[0].text


@pytest.mark.asyncio
async def test_execute_tool_preset_browser_workflow():
    """Test execute_tool with preset_browser_workflow tool."""
    # Create a mock controller
    controller = MagicMock()
    controller.client.browse_for_preset = MagicMock()
    controller.client.navigate_browser_filter = MagicMock()
    controller.client.navigate_browser_result = MagicMock()
    controller.client.commit_browser_selection = MagicMock()

    # Test with basic parameters
    result = await execute_tool(
        controller,
        "preset_browser_workflow",
        {
            "filter_navigations": [{"filter_index": 1, "steps": 2}],
            "result_navigations": 3,
        },
    )

    # Check that all required methods were called
    controller.client.browse_for_preset.assert_called_once()
    assert controller.client.navigate_browser_filter.call_count == 2
    assert controller.client.navigate_browser_result.call_count == 3
    controller.client.commit_browser_selection.assert_called_once()

    # Check the result
    assert "Preset browser workflow completed successfully" in result[0].text
