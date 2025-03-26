"""
Tests for the browser-related resources.

These tests verify that the MCP resources correctly handle browser-related
OSC messages and URIs.
"""

import pytest
from unittest.mock import MagicMock, patch

from bitwig_mcp_server.mcp.resources import (
    _read_browser_active_resource,
    _read_browser_tab_resource,
    _read_browser_filters_resource,
    _read_browser_filter_resource,
    _read_browser_filter_exists_resource,
    _read_browser_filter_name_resource,
    _read_browser_filter_wildcard_resource,
    _read_browser_filter_items_resource,
    _read_browser_filter_item_resource,
    _read_browser_filter_item_exists_resource,
    _read_browser_filter_item_name_resource,
    _read_browser_filter_item_hits_resource,
    _read_browser_filter_item_selected_resource,
    _read_browser_results_resource,
    _read_browser_result_resource,
    _read_browser_result_exists_resource,
    _read_browser_result_name_resource,
    _read_browser_result_selected_resource,
    read_resource,
)


@pytest.fixture
def mock_controller():
    """Create a mock controller for testing."""
    controller = MagicMock()
    controller.server = MagicMock()
    controller.client = MagicMock()

    # Set up some test responses for browser resources
    mock_responses = {
        "/browser/isActive": True,
        "/browser/tab": "Everything",
        "/browser/filter/1/exists": True,
        "/browser/filter/1/name": "Category",
        "/browser/filter/1/wildcard": "All",
        "/browser/filter/1/item/1/exists": True,
        "/browser/filter/1/item/1/name": "Effects",
        "/browser/filter/1/item/1/hits": 42,
        "/browser/filter/1/item/1/isSelected": True,
        "/browser/filter/2/exists": True,
        "/browser/filter/2/name": "Type",
        "/browser/filter/2/item/1/exists": True,
        "/browser/filter/2/item/1/name": "Distortion",
        "/browser/filter/2/item/1/isSelected": False,
        "/browser/result/1/exists": True,
        "/browser/result/1/name": "Amp",
        "/browser/result/1/isSelected": True,
        "/browser/result/2/exists": True,
        "/browser/result/2/name": "Distortion",
        "/browser/result/2/isSelected": False,
    }

    # Set up the mock to return values from the dictionary
    controller.server.get_message.side_effect = lambda key: mock_responses.get(key)

    return controller


def test_read_browser_active_resource(mock_controller):
    """Test reading browser active status."""
    result = _read_browser_active_resource(mock_controller)
    assert "Browser Active: True" in result
    mock_controller.server.get_message.assert_called_with("/browser/isActive")


def test_read_browser_tab_resource(mock_controller):
    """Test reading browser tab."""
    result = _read_browser_tab_resource(mock_controller)
    assert "Browser Tab: Everything" in result
    mock_controller.server.get_message.assert_called_with("/browser/tab")


def test_read_browser_filters_resource(mock_controller):
    """Test reading browser filters."""
    result = _read_browser_filters_resource(mock_controller)
    assert "Browser Filters:" in result
    assert "Filter 1: Category" in result
    assert "Filter 2: Type" in result
    assert "Effects" in result
    assert "Distortion" in result

    # Verify that the server.get_message was called for key browser paths
    mock_controller.server.get_message.assert_any_call("/browser/filter/1/exists")
    mock_controller.server.get_message.assert_any_call("/browser/filter/1/name")
    mock_controller.server.get_message.assert_any_call(
        "/browser/filter/1/item/1/exists"
    )
    mock_controller.server.get_message.assert_any_call("/browser/filter/1/item/1/name")


def test_read_browser_filter_resource(mock_controller):
    """Test reading browser filter."""
    result = _read_browser_filter_resource(mock_controller, 1)
    assert "Filter 1: Category" in result
    assert "Items:" in result
    assert "1: Effects" in result
    assert "[Selected]" in result

    # Test filter that doesn't exist
    mock_controller.server.get_message.side_effect = (
        lambda key: None if key == "/browser/filter/3/exists" else MagicMock()
    )
    with pytest.raises(ValueError):
        _read_browser_filter_resource(mock_controller, 3)


def test_read_browser_filter_exists_resource(mock_controller):
    """Test reading browser filter exists status."""
    result = _read_browser_filter_exists_resource(mock_controller, 1)
    assert "Filter 1 Exists: True" in result
    mock_controller.server.get_message.assert_called_with("/browser/filter/1/exists")


def test_read_browser_filter_name_resource(mock_controller):
    """Test reading browser filter name."""
    result = _read_browser_filter_name_resource(mock_controller, 1)
    assert "Filter 1 Name: Category" in result
    mock_controller.server.get_message.assert_any_call("/browser/filter/1/exists")
    mock_controller.server.get_message.assert_any_call("/browser/filter/1/name")

    # Test filter that doesn't exist
    mock_controller.server.get_message.side_effect = (
        lambda key: None if key == "/browser/filter/3/exists" else MagicMock()
    )
    with pytest.raises(ValueError):
        _read_browser_filter_name_resource(mock_controller, 3)


def test_read_browser_filter_wildcard_resource(mock_controller):
    """Test reading browser filter wildcard."""
    result = _read_browser_filter_wildcard_resource(mock_controller, 1)
    assert "Filter 1 Wildcard: All" in result
    mock_controller.server.get_message.assert_any_call("/browser/filter/1/exists")
    mock_controller.server.get_message.assert_any_call("/browser/filter/1/wildcard")

    # Test filter that doesn't exist
    mock_controller.server.get_message.side_effect = (
        lambda key: None if key == "/browser/filter/3/exists" else MagicMock()
    )
    with pytest.raises(ValueError):
        _read_browser_filter_wildcard_resource(mock_controller, 3)


def test_read_browser_filter_items_resource(mock_controller):
    """Test reading browser filter items."""
    result = _read_browser_filter_items_resource(mock_controller, 1)
    assert "Items for Filter 1: Category" in result
    assert "1: Effects" in result
    assert "[Selected]" in result

    # Test filter that doesn't exist
    mock_controller.server.get_message.side_effect = (
        lambda key: None if key == "/browser/filter/3/exists" else MagicMock()
    )
    with pytest.raises(ValueError):
        _read_browser_filter_items_resource(mock_controller, 3)


def test_read_browser_filter_item_resource(mock_controller):
    """Test reading browser filter item."""
    result = _read_browser_filter_item_resource(mock_controller, 1, 1)
    assert "Filter 1, Item 1: Effects" in result
    assert "Selected: True" in result
    assert "Hits: 42" in result

    # Test filter that doesn't exist
    mock_controller.server.get_message.side_effect = (
        lambda key: None if key == "/browser/filter/3/exists" else MagicMock()
    )
    with pytest.raises(ValueError):
        _read_browser_filter_item_resource(mock_controller, 3, 1)

    # Test item that doesn't exist
    mock_controller.server.get_message.side_effect = (
        lambda key: None if key == "/browser/filter/1/item/3/exists" else MagicMock()
    )
    with pytest.raises(ValueError):
        _read_browser_filter_item_resource(mock_controller, 1, 3)


def test_read_browser_filter_item_exists_resource(mock_controller):
    """Test reading browser filter item exists status."""
    result = _read_browser_filter_item_exists_resource(mock_controller, 1, 1)
    assert "Filter 1, Item 1 Exists: True" in result
    mock_controller.server.get_message.assert_any_call("/browser/filter/1/exists")
    mock_controller.server.get_message.assert_any_call(
        "/browser/filter/1/item/1/exists"
    )

    # Test filter that doesn't exist
    mock_controller.server.get_message.side_effect = (
        lambda key: None if key == "/browser/filter/3/exists" else MagicMock()
    )
    with pytest.raises(ValueError):
        _read_browser_filter_item_exists_resource(mock_controller, 3, 1)


def test_read_browser_filter_item_name_resource(mock_controller):
    """Test reading browser filter item name."""
    result = _read_browser_filter_item_name_resource(mock_controller, 1, 1)
    assert "Filter 1, Item 1 Name: Effects" in result
    mock_controller.server.get_message.assert_any_call("/browser/filter/1/exists")
    mock_controller.server.get_message.assert_any_call(
        "/browser/filter/1/item/1/exists"
    )
    mock_controller.server.get_message.assert_any_call("/browser/filter/1/item/1/name")

    # Test filter that doesn't exist
    mock_controller.server.get_message.side_effect = (
        lambda key: None if key == "/browser/filter/3/exists" else MagicMock()
    )
    with pytest.raises(ValueError):
        _read_browser_filter_item_name_resource(mock_controller, 3, 1)

    # Test item that doesn't exist
    mock_controller.server.get_message.side_effect = (
        lambda key: None if key == "/browser/filter/1/item/3/exists" else MagicMock()
    )
    with pytest.raises(ValueError):
        _read_browser_filter_item_name_resource(mock_controller, 1, 3)


def test_read_browser_filter_item_hits_resource(mock_controller):
    """Test reading browser filter item hits."""
    result = _read_browser_filter_item_hits_resource(mock_controller, 1, 1)
    assert "Filter 1, Item 1 Hits: 42" in result
    mock_controller.server.get_message.assert_any_call("/browser/filter/1/exists")
    mock_controller.server.get_message.assert_any_call(
        "/browser/filter/1/item/1/exists"
    )
    mock_controller.server.get_message.assert_any_call("/browser/filter/1/item/1/hits")

    # Test filter that doesn't exist
    mock_controller.server.get_message.side_effect = (
        lambda key: None if key == "/browser/filter/3/exists" else MagicMock()
    )
    with pytest.raises(ValueError):
        _read_browser_filter_item_hits_resource(mock_controller, 3, 1)

    # Test item that doesn't exist
    mock_controller.server.get_message.side_effect = (
        lambda key: None if key == "/browser/filter/1/item/3/exists" else MagicMock()
    )
    with pytest.raises(ValueError):
        _read_browser_filter_item_hits_resource(mock_controller, 1, 3)


def test_read_browser_filter_item_selected_resource(mock_controller):
    """Test reading browser filter item selected status."""
    result = _read_browser_filter_item_selected_resource(mock_controller, 1, 1)
    assert "Filter 1, Item 1 Selected: True" in result
    mock_controller.server.get_message.assert_any_call("/browser/filter/1/exists")
    mock_controller.server.get_message.assert_any_call(
        "/browser/filter/1/item/1/exists"
    )
    mock_controller.server.get_message.assert_any_call(
        "/browser/filter/1/item/1/isSelected"
    )

    # Test filter that doesn't exist
    mock_controller.server.get_message.side_effect = (
        lambda key: None if key == "/browser/filter/3/exists" else MagicMock()
    )
    with pytest.raises(ValueError):
        _read_browser_filter_item_selected_resource(mock_controller, 3, 1)

    # Test item that doesn't exist
    mock_controller.server.get_message.side_effect = (
        lambda key: None if key == "/browser/filter/1/item/3/exists" else MagicMock()
    )
    with pytest.raises(ValueError):
        _read_browser_filter_item_selected_resource(mock_controller, 1, 3)


def test_read_browser_results_resource(mock_controller):
    """Test reading browser results."""
    result = _read_browser_results_resource(mock_controller)
    assert "Browser Results:" in result
    assert "1: Amp [Selected]" in result
    assert "2: Distortion" in result

    # Verify that the server.get_message was called for key browser paths
    mock_controller.server.get_message.assert_any_call("/browser/result/1/exists")
    mock_controller.server.get_message.assert_any_call("/browser/result/1/name")
    mock_controller.server.get_message.assert_any_call("/browser/result/1/isSelected")
    mock_controller.server.get_message.assert_any_call("/browser/result/2/exists")


def test_read_browser_result_resource(mock_controller):
    """Test reading browser result."""
    result = _read_browser_result_resource(mock_controller, 1)
    assert "Result 1: Amp" in result
    assert "Selected: True" in result

    # Test result that doesn't exist
    mock_controller.server.get_message.side_effect = (
        lambda key: None if key == "/browser/result/3/exists" else MagicMock()
    )
    with pytest.raises(ValueError):
        _read_browser_result_resource(mock_controller, 3)


def test_read_browser_result_exists_resource(mock_controller):
    """Test reading browser result exists status."""
    result = _read_browser_result_exists_resource(mock_controller, 1)
    assert "Result 1 Exists: True" in result
    mock_controller.server.get_message.assert_called_with("/browser/result/1/exists")


def test_read_browser_result_name_resource(mock_controller):
    """Test reading browser result name."""
    result = _read_browser_result_name_resource(mock_controller, 1)
    assert "Result 1 Name: Amp" in result
    mock_controller.server.get_message.assert_any_call("/browser/result/1/exists")
    mock_controller.server.get_message.assert_any_call("/browser/result/1/name")

    # Test result that doesn't exist
    mock_controller.server.get_message.side_effect = (
        lambda key: None if key == "/browser/result/3/exists" else MagicMock()
    )
    with pytest.raises(ValueError):
        _read_browser_result_name_resource(mock_controller, 3)


def test_read_browser_result_selected_resource(mock_controller):
    """Test reading browser result selected status."""
    result = _read_browser_result_selected_resource(mock_controller, 1)
    assert "Result 1 Selected: True" in result
    mock_controller.server.get_message.assert_any_call("/browser/result/1/exists")
    mock_controller.server.get_message.assert_any_call("/browser/result/1/isSelected")

    # Test result that doesn't exist
    mock_controller.server.get_message.side_effect = (
        lambda key: None if key == "/browser/result/3/exists" else MagicMock()
    )
    with pytest.raises(ValueError):
        _read_browser_result_selected_resource(mock_controller, 3)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "uri,expected",
    [
        ("bitwig://browser/isActive", "Browser Active: True"),
        ("bitwig://browser/tab", "Browser Tab: Everything"),
        ("bitwig://browser/filter/1/exists", "Filter 1 Exists: True"),
        ("bitwig://browser/filter/1/name", "Filter 1 Name: Category"),
        ("bitwig://browser/filter/1/wildcard", "Filter 1 Wildcard: All"),
        ("bitwig://browser/filter/1/item/1/exists", "Filter 1, Item 1 Exists: True"),
        ("bitwig://browser/filter/1/item/1/name", "Filter 1, Item 1 Name: Effects"),
        ("bitwig://browser/filter/1/item/1/hits", "Filter 1, Item 1 Hits: 42"),
        (
            "bitwig://browser/filter/1/item/1/isSelected",
            "Filter 1, Item 1 Selected: True",
        ),
        ("bitwig://browser/result/1/exists", "Result 1 Exists: True"),
        ("bitwig://browser/result/1/name", "Result 1 Name: Amp"),
        ("bitwig://browser/result/1/isSelected", "Result 1 Selected: True"),
    ],
)
async def test_read_resource_browser_uris(mock_controller, uri, expected):
    """Test reading resources with browser URIs."""
    # Patch the client.refresh method to avoid side effects
    mock_controller.client.refresh = MagicMock()

    # First, create a mock for the _read_* functions to ensure they return
    # the expected string instead of testing the real implementation
    with (
        patch(
            "bitwig_mcp_server.mcp.resources._read_browser_active_resource",
            return_value="Browser Active: True",
        ),
        patch(
            "bitwig_mcp_server.mcp.resources._read_browser_tab_resource",
            return_value="Browser Tab: Everything",
        ),
        patch(
            "bitwig_mcp_server.mcp.resources._read_browser_filter_exists_resource",
            return_value="Filter 1 Exists: True",
        ),
        patch(
            "bitwig_mcp_server.mcp.resources._read_browser_filter_name_resource",
            return_value="Filter 1 Name: Category",
        ),
        patch(
            "bitwig_mcp_server.mcp.resources._read_browser_filter_wildcard_resource",
            return_value="Filter 1 Wildcard: All",
        ),
        patch(
            "bitwig_mcp_server.mcp.resources._read_browser_filter_item_exists_resource",
            return_value="Filter 1, Item 1 Exists: True",
        ),
        patch(
            "bitwig_mcp_server.mcp.resources._read_browser_filter_item_name_resource",
            return_value="Filter 1, Item 1 Name: Effects",
        ),
        patch(
            "bitwig_mcp_server.mcp.resources._read_browser_filter_item_hits_resource",
            return_value="Filter 1, Item 1 Hits: 42",
        ),
        patch(
            "bitwig_mcp_server.mcp.resources._read_browser_filter_item_selected_resource",
            return_value="Filter 1, Item 1 Selected: True",
        ),
        patch(
            "bitwig_mcp_server.mcp.resources._read_browser_result_exists_resource",
            return_value="Result 1 Exists: True",
        ),
        patch(
            "bitwig_mcp_server.mcp.resources._read_browser_result_name_resource",
            return_value="Result 1 Name: Amp",
        ),
        patch(
            "bitwig_mcp_server.mcp.resources._read_browser_result_selected_resource",
            return_value="Result 1 Selected: True",
        ),
    ):
        result = await read_resource(mock_controller, uri)
        assert expected in result


@pytest.mark.asyncio
async def test_read_resource_browser_invalid_uris(mock_controller):
    """Test reading resources with invalid browser URIs."""
    # Patch the client.refresh method to avoid side effects
    mock_controller.client.refresh = MagicMock()

    # Test invalid browser URIs
    with pytest.raises(ValueError):
        await read_resource(mock_controller, "bitwig://browser/invalid")

    with pytest.raises(ValueError):
        await read_resource(mock_controller, "bitwig://browser/filter/invalid")

    with pytest.raises(ValueError):
        await read_resource(mock_controller, "bitwig://browser/filter/1/item/invalid")
