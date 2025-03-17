"""Tests for the BitwigOSCClient class"""

import unittest
from unittest.mock import MagicMock

from bitwig_mcp_server.osc.client import BitwigOSCClient


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

        self.client.play()
        self.client.client.send_message.assert_called_with("/play", None)

        # Test stop
        self.client.stop()
        self.client.client.send_message.assert_called_with("/stop", 1)

        # Test tempo
        self.client.set_tempo(120.5)
        self.client.client.send_message.assert_called_with("/tempo/raw", 120.5)

        # Test tempo clamping
        self.client.set_tempo(700)
        self.client.client.send_message.assert_called_with("/tempo/raw", 666)

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
