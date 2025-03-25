"""Tests for the BitwigOSCClient class"""

import unittest
from unittest.mock import MagicMock

import pytest

from bitwig_mcp_server.osc.client import BitwigOSCClient
from bitwig_mcp_server.osc.exceptions import InvalidParameterError


class TestBitwigOSCClient(unittest.TestCase):
    """Test cases for BitwigOSCClient"""

    def setUp(self):
        """Set up test environment"""
        self.client = BitwigOSCClient()
        self.client.client = MagicMock()  # Mock the underlying UDP client

    def test_send(self):
        """Test sending OSC messages"""
        self.client.send("/test/address", 42)
        self.client.client.send_message.assert_called_once_with("/test/address", 42)
        self.assertEqual(self.client.addr_log, ["/test/address"])

    def test_transport_controls(self):
        """Test transport control methods"""
        # Test play with different states
        self.client.play(True)
        self.client.client.send_message.assert_called_with("/play", 1)

        self.client.play(False)
        self.client.client.send_message.assert_called_with("/play", 0)

    def test_device_controls(self):
        """Test device control methods"""
        # Test toggle device bypass
        self.client.toggle_device_bypass()
        self.client.client.send_message.assert_called_with("/device/bypass", None)

        # Test select device sibling
        self.client.select_device_sibling(3)
        self.client.client.send_message.assert_called_with(
            "/device/sibling/3/select", 1
        )

        # Test select device by index
        self.client.select_device_by_index(2)
        self.client.client.send_message.assert_called_with("/device/select/2", 1)

        # Test select invalid device index
        with pytest.raises(InvalidParameterError):
            self.client.select_device_by_index(0)  # Below range

        # Test select invalid sibling
        with pytest.raises(InvalidParameterError):
            self.client.select_device_sibling(0)  # Below range
        with pytest.raises(InvalidParameterError):
            self.client.select_device_sibling(9)  # Above range

        # Test navigate device next
        self.client.navigate_device("next")
        self.client.client.send_message.assert_called_with("/device/+", None)

        # Test navigate device previous
        self.client.navigate_device("previous")
        self.client.client.send_message.assert_called_with("/device/-", None)

        # Test invalid navigation direction
        with pytest.raises(InvalidParameterError):
            self.client.navigate_device("invalid")

        # Test enter device layer
        self.client.enter_device_layer(2)
        self.client.client.send_message.assert_called_with(
            "/device/layer/2/enter", None
        )

        # Test exit device layer
        self.client.exit_device_layer()
        self.client.client.send_message.assert_called_with("/device/layer/parent", None)

        # Test toggle device window
        self.client.toggle_device_window()
        self.client.client.send_message.assert_called_with("/device/window", None)

        self.client.play()
        self.client.client.send_message.assert_called_with("/play", None)

        # Test stop
        self.client.stop()
        self.client.client.send_message.assert_called_with("/stop", 1)

        # Test tempo
        self.client.set_tempo(120.5)
        self.client.client.send_message.assert_called_with("/tempo/raw", 120.5)

        # Test tempo clamping
        self.client.set_tempo(1200)
        self.client.client.send_message.assert_called_with("/tempo/raw", 999)

    def test_track_controls(self):
        """Test track control methods"""
        # Test volume
        self.client.set_track_volume(1, 64)
        self.client.client.send_message.assert_called_with("/track/1/volume", 64)

        # Test pan
        self.client.set_track_pan(2, 32)
        self.client.client.send_message.assert_called_with("/track/2/pan", 32)

        # Test mute
        self.client.set_track_mute(3, True)
        self.client.client.send_message.assert_called_with("/track/3/mute", 1)

        self.client.toggle_track_mute(4)
        self.client.client.send_message.assert_called_with("/track/4/mute", None)


if __name__ == "__main__":
    unittest.main()
