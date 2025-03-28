"""
Tests for the Bitwig MCP Server resources module.
"""

from unittest.mock import MagicMock, patch

import pytest
import bitwig_mcp_server.mcp.resources

from bitwig_mcp_server.mcp.resources import (
    get_bitwig_resources,
    read_resource,
    _read_transport_resource,
    _read_tracks_resource,
    _read_track_resource,
    _read_devices_resource,
    _read_device_parameters_resource,
    _read_device_siblings_resource,
    _read_device_layers_resource,
    _read_device_resource_by_index,
    _read_device_parameters_resource_by_index,
)


def test_get_bitwig_resources():
    """Test that get_bitwig_resources returns the expected resources."""
    resources = get_bitwig_resources()

    # Check that we have at least the minimum number of expected resources
    # This is a flexible test that allows for new resources to be added over time
    assert len(resources) >= 9

    # Check that the resources have the expected URIs
    # Resource URIs are converted to Pydantic AnyUrl objects by the MCP SDK,
    # so we compare the string representations with URL-encoded characters where needed
    resource_uri_strings = {str(resource.uri) for resource in resources}

    # Define the minimum set of URIs we expect to see
    # This approach is more flexible and allows new resources to be added without breaking tests
    minimum_expected_uris = {
        "bitwig://transport",
        "bitwig://tracks",
        "bitwig://track/%7Bindex%7D",  # URL-encoded {index}
        "bitwig://devices",
        "bitwig://device/parameters",
        "bitwig://device/%7Bindex%7D",  # URL-encoded {index}
        "bitwig://device/%7Bindex%7D/parameters",  # URL-encoded {index}/parameters
        "bitwig://device/siblings",
        "bitwig://device/layers",
    }

    # Check that all of our minimum expected URIs are present
    assert minimum_expected_uris.issubset(
        resource_uri_strings
    ), f"Missing expected URIs: {minimum_expected_uris - resource_uri_strings}"

    # Print the full list of resources for debugging
    print(f"Current resources ({len(resources)}):")
    for uri in sorted(resource_uri_strings):
        print(f"  - {uri}")

    # Check resource structure
    for resource in resources:
        assert hasattr(resource, "name")
        assert hasattr(resource, "description")
        assert hasattr(resource, "mimeType")
        assert resource.mimeType == "text/plain"


@pytest.mark.asyncio
async def test_read_resource_transport():
    """Test read_resource with transport resource."""
    # Create mock controller
    controller = MagicMock()
    controller.client = MagicMock()
    controller.server = MagicMock()

    # Mock _read_transport_resource function
    with patch("bitwig_mcp_server.mcp.resources._read_transport_resource") as mock_read:
        mock_read.return_value = "Transport info"

        # Read the resource
        result = await read_resource(controller, "bitwig://transport")

        # Check that refresh was called
        controller.client.refresh.assert_called_once()

        # Check that the mock function was called
        mock_read.assert_called_once_with(controller)

        # Check the result
        assert result == "Transport info"


@pytest.mark.asyncio
async def test_read_resource_tracks():
    """Test read_resource with tracks resource."""
    # Create mock controller
    controller = MagicMock()
    controller.client = MagicMock()
    controller.server = MagicMock()

    # Mock _read_tracks_resource function
    with patch("bitwig_mcp_server.mcp.resources._read_tracks_resource") as mock_read:
        mock_read.return_value = "Tracks info"

        # Read the resource
        result = await read_resource(controller, "bitwig://tracks")

        # Check that refresh was called
        controller.client.refresh.assert_called_once()

        # Check that the mock function was called
        mock_read.assert_called_once_with(controller)

        # Check the result
        assert result == "Tracks info"


@pytest.mark.asyncio
async def test_read_resource_track():
    """Test read_resource with track resource."""
    # Create mock controller
    controller = MagicMock()
    controller.client = MagicMock()
    controller.server = MagicMock()

    # Mock _read_track_resource function
    with patch("bitwig_mcp_server.mcp.resources._read_track_resource") as mock_read:
        mock_read.return_value = "Track info"

        # Read the resource
        result = await read_resource(controller, "bitwig://track/1")

        # Check that refresh was called
        controller.client.refresh.assert_called_once()

        # Check that the mock function was called with correct track index
        mock_read.assert_called_once_with(controller, 1)

        # Check the result
        assert result == "Track info"


@pytest.mark.asyncio
async def test_read_resource_invalid_track_uri():
    """Test read_resource with invalid track URI."""
    # Create mock controller
    controller = MagicMock()
    controller.client = MagicMock()

    # Read with invalid URI
    with pytest.raises(ValueError, match="Invalid track URI"):
        await read_resource(controller, "bitwig://track/invalid")


@pytest.mark.asyncio
async def test_read_resource_unknown():
    """Test read_resource with unknown resource."""
    # Create mock controller
    controller = MagicMock()
    controller.client = MagicMock()

    # Read with unknown URI
    with pytest.raises(ValueError, match="Unknown resource URI"):
        await read_resource(controller, "bitwig://unknown")


def test_read_transport_resource():
    """Test _read_transport_resource function."""
    # Create mock controller
    controller = MagicMock()
    controller.server = MagicMock()

    # Configure mock to return specific values
    controller.server.get_message.side_effect = lambda addr: {
        "/play": True,
        "/tempo/raw": 120.5,
        "/signature/numerator": 4,
        "/signature/denominator": 4,
    }.get(addr)

    # Read the transport resource
    result = _read_transport_resource(controller)

    # Check the result contains expected information
    assert "Transport State:" in result
    assert "Playing: True" in result
    assert "Tempo: 120.5 BPM" in result
    assert "Time Signature: 4/4" in result


def test_read_tracks_resource():
    """Test _read_tracks_resource function."""
    # Create mock controller
    controller = MagicMock()
    controller.server = MagicMock()

    # Configure mock to return specific values for track 1
    def mock_get_message(addr):
        if addr == "/track/1/name":
            return "Track 1"
        elif addr == "/track/1/volume":
            return 64
        elif addr == "/track/1/pan":
            return 64
        elif addr == "/track/1/mute":
            return 0
        elif addr == "/track/1/solo":
            return 0
        elif addr == "/track/1/recarm":
            return 1
        # Return None for other tracks
        elif addr.startswith("/track/"):
            return None if "/name" in addr else None
        return None

    controller.server.get_message.side_effect = mock_get_message

    # Read the tracks resource
    result = _read_tracks_resource(controller)

    # Check the result contains expected information
    assert "Tracks:" in result
    assert "Track 1: Track 1" in result
    assert "Volume: 64" in result
    assert "Pan: 64" in result
    assert "Mute: False" in result
    assert "Solo: False" in result
    assert "Record Armed: True" in result


def test_read_track_resource():
    """Test _read_track_resource function."""
    # Create mock controller
    controller = MagicMock()
    controller.server = MagicMock()

    # Configure mock to return specific values for track
    def mock_get_message(addr):
        if addr == "/track/1/name":
            return "Track 1"
        elif addr == "/track/1/type":
            return "Audio"
        elif addr == "/track/1/volume":
            return 64
        elif addr == "/track/1/pan":
            return 64
        elif addr == "/track/1/mute":
            return 0
        elif addr == "/track/1/solo":
            return 0
        elif addr == "/track/1/recarm":
            return 1
        elif addr == "/track/1/color":
            return "blue"
        elif addr == "/track/1/sends":
            return 2
        return None

    controller.server.get_message.side_effect = mock_get_message

    # Read the track resource
    result = _read_track_resource(controller, 1)

    # Check the result contains expected information
    assert "Track: Track 1" in result
    assert "Index: 1" in result
    assert "Type: Audio" in result
    assert "Volume: 64" in result
    assert "Pan: 64" in result
    assert "Mute: False" in result
    assert "Solo: False" in result
    assert "Record Armed: True" in result
    assert "Color: blue" in result
    assert "Send Count: 2" in result


def test_read_track_resource_not_found():
    """Test _read_track_resource function with non-existent track."""
    # Create mock controller
    controller = MagicMock()
    controller.server = MagicMock()

    # Configure mock to return None for track name (track not found)
    controller.server.get_message.return_value = None

    # Read non-existent track
    with pytest.raises(ValueError, match="Track 1 not found"):
        _read_track_resource(controller, 1)


def test_read_devices_resource():
    """Test _read_devices_resource function."""
    # Create mock controller
    controller = MagicMock()
    controller.server = MagicMock()

    # Configure mock to return specific values
    def mock_get_message(addr):
        if addr == "/device/exists":
            return 1
        elif addr == "/device/name":
            return "EQ-5"
        elif addr == "/device/chain/size":
            return 2
        elif addr == "/device/chain/1/name":
            return "Filter"
        elif addr == "/device/chain/2/name":
            return "Compressor"
        return None

    controller.server.get_message.side_effect = mock_get_message

    # Read the devices resource
    result = _read_devices_resource(controller)

    # Check the result contains expected information
    assert "Active Device: EQ-5" in result
    assert "Device Chain Size: 2" in result
    assert "1: Filter" in result
    assert "2: Compressor" in result


def test_read_device_parameters_resource():
    """Test _read_device_parameters_resource function."""
    # Create mock controller
    controller = MagicMock()
    controller.server = MagicMock()

    # Configure mock to return specific values
    def mock_get_message(addr):
        if addr == "/device/exists":
            return 1
        elif addr == "/device/name":
            return "EQ-5"
        elif addr == "/device/param/1/exists":
            return 1
        elif addr == "/device/param/1/name":
            return "Frequency"
        elif addr == "/device/param/1/value":
            return 64
        elif addr == "/device/param/1/value/str":
            return "1000 Hz"
        elif addr == "/device/param/2/exists":
            return 1
        elif addr == "/device/param/2/name":
            return "Gain"
        elif addr == "/device/param/2/value":
            return 32
        elif addr == "/device/param/2/value/str":
            return "+3 dB"
        elif addr.startswith("/device/param/"):
            return 0 if "/exists" in addr else None
        return None

    controller.server.get_message.side_effect = mock_get_message

    # Read the device parameters resource
    result = _read_device_parameters_resource(controller)

    # Check the result contains expected information
    assert "Device: EQ-5" in result
    assert "Parameters:" in result
    assert "1: Frequency = 64 (1000 Hz)" in result
    assert "2: Gain = 32 (+3 dB)" in result


@pytest.mark.asyncio
async def test_read_resource_device_siblings():
    """Test read_resource with device siblings resource."""
    # Create mock controller
    controller = MagicMock()
    controller.client = MagicMock()
    controller.server = MagicMock()

    # We'll mock the _read_device_siblings_resource directly
    with patch.object(
        bitwig_mcp_server.mcp.resources, "_read_device_siblings_resource"
    ) as mock_read:
        mock_read.return_value = "Device siblings info"

        # Read the resource
        result = await read_resource(controller, "bitwig://device/siblings")

        # Check that refresh was called
        controller.client.refresh.assert_called_once()

        # Check the result
        assert result == "Device siblings info"


@pytest.mark.asyncio
async def test_read_resource_device_layers():
    """Test read_resource with device layers resource."""
    # Create mock controller
    controller = MagicMock()
    controller.client = MagicMock()
    controller.server = MagicMock()

    # We'll mock the _read_device_layers_resource directly
    with patch.object(
        bitwig_mcp_server.mcp.resources, "_read_device_layers_resource"
    ) as mock_read:
        mock_read.return_value = "Device layers info"

        # Read the resource
        result = await read_resource(controller, "bitwig://device/layers")

        # Check that refresh was called
        controller.client.refresh.assert_called_once()

        # Check the result
        assert result == "Device layers info"


def test_read_device_siblings_resource():
    """Test _read_device_siblings_resource function."""
    # Create mock controller
    controller = MagicMock()
    controller.server = MagicMock()

    # Configure mock to return specific values
    def mock_get_message(addr):
        if addr == "/device/exists":
            return 1
        elif addr == "/device/name":
            return "Compressor"
        elif addr == "/device/chain/size":
            return 3
        elif addr == "/device/sibling/1/name":
            return "EQ-5"
        elif addr == "/device/sibling/1/exists":
            return 1
        elif addr == "/device/sibling/1/bypass":
            return 0
        elif addr == "/device/sibling/2/name":
            return "Compressor"  # Current device
        elif addr == "/device/sibling/2/exists":
            return 1
        elif addr == "/device/sibling/2/bypass":
            return 0
        elif addr == "/device/sibling/3/name":
            return "Limiter"
        elif addr == "/device/sibling/3/exists":
            return 1
        elif addr == "/device/sibling/3/bypass":
            return 1
        return None

    controller.server.get_message.side_effect = mock_get_message

    # Read the device siblings resource
    result = _read_device_siblings_resource(controller)

    # Check the result contains expected information
    assert "Current Device: Compressor" in result
    assert "Sibling Devices:" in result
    assert "1: EQ-5" in result
    assert "Bypassed: False" in result
    assert "3: Limiter" in result
    assert "Bypassed: True" in result


def test_read_device_layers_resource():
    """Test _read_device_layers_resource function."""
    # Create mock controller
    controller = MagicMock()
    controller.server = MagicMock()

    # Configure mock to return specific values
    def mock_get_message(addr):
        if addr == "/device/exists":
            return 1
        elif addr == "/device/name":
            return "Instrument Rack"
        elif addr == "/device/layer/exists":
            return 2  # Number of layers
        elif addr == "/device/layer/1/exists":
            return 1
        elif addr == "/device/layer/1/name":
            return "Piano Layer"
        elif addr == "/device/layer/1/chain/size":
            return 3
        elif addr == "/device/layer/2/exists":
            return 1
        elif addr == "/device/layer/2/name":
            return "Synth Layer"
        elif addr == "/device/layer/2/chain/size":
            return 2
        return None

    controller.server.get_message.side_effect = mock_get_message

    # Read the device layers resource
    result = _read_device_layers_resource(controller)

    # Check the result contains expected information
    assert "Device: Instrument Rack" in result
    assert "Layers:" in result
    assert "1: Piano Layer" in result
    assert "Contains 3 devices" in result
    assert "2: Synth Layer" in result
    assert "Contains 2 devices" in result


def test_read_device_siblings_resource_no_siblings():
    """Test _read_device_siblings_resource function with no siblings."""
    # Create mock controller
    controller = MagicMock()
    controller.server = MagicMock()

    # Configure mock to return values for a device with no siblings
    def mock_get_message(addr):
        if addr == "/device/exists":
            return 1
        elif addr == "/device/name":
            return "Reverb"
        elif addr == "/device/chain/size":
            return 1  # Only one device in chain (itself)
        elif addr.startswith("/device/sibling/"):
            return None  # No siblings
        return None

    controller.server.get_message.side_effect = mock_get_message

    # Read the device siblings resource
    result = _read_device_siblings_resource(controller)

    # Check the result indicates no siblings found
    assert "No sibling devices found" in result


def test_read_device_layers_resource_no_layers():
    """Test _read_device_layers_resource function with a device that has no layers."""
    # Create mock controller
    controller = MagicMock()
    controller.server = MagicMock()

    # Configure mock to return values for a device without layers
    def mock_get_message(addr):
        if addr == "/device/exists":
            return 1
        elif addr == "/device/name":
            return "Reverb"
        elif addr == "/device/layer/exists":
            return 0  # No layers
        return None

    controller.server.get_message.side_effect = mock_get_message

    # Read the device layers resource
    result = _read_device_layers_resource(controller)

    # Check the result indicates no layers found
    assert "No device layers found" in result


@pytest.mark.asyncio
async def test_read_resource_device_by_index():
    """Test read_resource with device by index resource."""
    # This test will manually check the logic in read_resource to debug the issue

    # Create URI with device index
    uri = "bitwig://device/1"

    # Test the URI parsing with the proper urlparse
    from urllib.parse import urlparse

    parsed_uri = urlparse(uri)
    print(f"\nParsed URI: {parsed_uri}")
    print(f"Scheme: {parsed_uri.scheme}")
    print(f"NetLoc: {parsed_uri.netloc}")
    print(f"Path: {parsed_uri.path}")

    # Get the path component and check our logic
    path = parsed_uri.path.lstrip("/")
    path_parts = path.split("/")
    print(f"Path parts: {path_parts}")

    # Check if parts match our expected pattern
    if len(path_parts) == 1 and path_parts[0].isdigit():
        print("URI matches pattern for device/{index}")
        device_index = int(path_parts[0])
        print(f"Extracted device index: {device_index}")
    else:
        print("URI does NOT match pattern for device/{index}")

    # Now test the read_resource function with proper mocking
    controller = MagicMock()
    controller.client = MagicMock()
    controller.server = MagicMock()

    # Mock the _read_device_resource_by_index to return a predictable value
    with patch.object(
        bitwig_mcp_server.mcp.resources, "_read_device_resource_by_index"
    ) as mock_resource_func:
        # Set up the return value
        mock_resource_func.return_value = "Mocked device info"

        # Call read_resource with our URI
        # We now expect this to work properly with the fixed parsing logic
        result = await read_resource(controller, uri)

        # The test should now pass with the fixed URI parsing
        assert result == "Mocked device info"

        # And we should verify the mock was called with the correct parameters
        mock_resource_func.assert_called_once_with(controller, 1)


@pytest.mark.asyncio
async def test_read_resource_device_parameters_by_index():
    """Test read_resource with device parameters by index resource."""
    # Create URI with device index and parameters
    uri = "bitwig://device/1/parameters"

    # Parse the URI to verify our logic
    from urllib.parse import urlparse

    parsed_uri = urlparse(uri)
    print(f"\nParsed URI for parameters: {parsed_uri}")
    print(f"Scheme: {parsed_uri.scheme}")
    print(f"NetLoc: {parsed_uri.netloc}")
    print(f"Path: {parsed_uri.path}")

    # Get the path component and verify
    path = parsed_uri.path.lstrip("/")
    path_parts = path.split("/")
    print(f"Path parts: {path_parts}")

    # Check if parts match our expected pattern
    if (
        len(path_parts) == 2
        and path_parts[0].isdigit()
        and path_parts[1] == "parameters"
    ):
        print("URI matches pattern for device/{index}/parameters")
        device_index = int(path_parts[0])
        print(f"Extracted device index: {device_index}")
    else:
        print("URI does NOT match pattern for device/{index}/parameters")

    # Create mock controller
    controller = MagicMock()
    controller.client = MagicMock()
    controller.server = MagicMock()

    # Mock the parameter resource function
    with patch.object(
        bitwig_mcp_server.mcp.resources, "_read_device_parameters_resource_by_index"
    ) as mock_func:
        # Set up return value
        mock_func.return_value = "Mocked device parameters"

        # Call read_resource with our URI
        result = await read_resource(controller, uri)

        # The test should now pass with the fixed URI parsing
        assert result == "Mocked device parameters"

        # Verify the mock was called with the correct parameters
        mock_func.assert_called_once_with(controller, 1)


def test_read_device_resource_by_index():
    """Test _read_device_resource_by_index function."""
    # Create mock controller
    controller = MagicMock()
    controller.client = MagicMock()
    controller.server = MagicMock()

    # Configure mock to return values for a device
    def mock_get_message(addr):
        if addr == "/device/exists":
            return 1
        elif addr == "/device/name":
            return "Compressor"
        elif addr == "/device/bypass":
            return 0
        elif addr == "/device/chain/size":
            return 3
        elif addr == "/device/preset/name":
            return "Default"
        elif addr == "/device/category":
            return "Dynamics"
        return None

    controller.server.get_message.side_effect = mock_get_message

    # Read the device resource by index
    result = _read_device_resource_by_index(controller, 2)

    # Check the select method was called with correct index
    controller.client.select_device_by_index.assert_called_once_with(2)

    # Check the result contains expected information
    assert "Device: Compressor" in result
    assert "Index: 2" in result
    assert "Bypassed: False" in result
    assert "Chain Size: 3" in result
    assert "Preset: Default" in result
    assert "Category: Dynamics" in result


def test_read_device_parameters_resource_by_index():
    """Test _read_device_parameters_resource_by_index function."""
    # Create mock controller
    controller = MagicMock()
    controller.client = MagicMock()
    controller.server = MagicMock()

    # Configure mock to return values for device exists check
    controller.server.get_message.return_value = 1

    # Mock the _read_device_parameters_resource function
    with patch(
        "bitwig_mcp_server.mcp.resources._read_device_parameters_resource"
    ) as mock_read:
        mock_read.return_value = "Device parameters content"

        # Read the device parameters resource by index
        result = _read_device_parameters_resource_by_index(controller, 3)

        # Check the select method was called with correct index
        controller.client.select_device_by_index.assert_called_once_with(3)

        # Check that the internal function was called
        mock_read.assert_called_once_with(controller)

        # Check the result
        assert result == "Device parameters content"
