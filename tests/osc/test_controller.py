"""Tests for the BitwigOSCController class"""

import unittest
from unittest.mock import MagicMock, patch

from bitwig_mcp_server.osc.controller import BitwigOSCController


class TestBitwigOSCController(unittest.TestCase):
    """Test cases for BitwigOSCController"""

    def setUp(self):
        """Set up test environment"""
        # Create controller with mocked client and server
        with (
            patch("bitwig_mcp_server.osc.controller.BitwigOSCClient") as mock_client_class,
            patch("bitwig_mcp_server.osc.controller.BitwigOSCServer") as mock_server_class,
        ):
            self.mock_client = MagicMock()
            self.mock_server = MagicMock()

            mock_client_class.return_value = self.mock_client
            mock_server_class.return_value = self.mock_server

            self.controller = BitwigOSCController()

    def test_start_stop(self):
        """Test starting and stopping controller"""
        # Test start
        self.controller.start()
        self.mock_server.start.assert_called_once()
        self.mock_client.refresh.assert_called_once()
        self.assertTrue(self.controller.ready)

        # Test stop
        self.controller.stop()
        self.mock_server.stop.assert_called_once()

    def test_context_manager(self):
        """Test context manager protocol"""
        with patch.object(self.controller, "start") as mock_start, patch.object(self.controller, "stop") as mock_stop:
            with self.controller:
                mock_start.assert_called_once()

            mock_stop.assert_called_once()

    def test_send_and_wait(self):
        """Test sending command and waiting for response"""
        # Set up mock response
        self.mock_server.received_messages = {"/test/response": None}
        self.mock_server.wait_for_message.return_value = 42

        # Test with default response address
        result = self.controller.send_and_wait("/test/command", 1)
        self.mock_client.send.assert_called_with("/test/command", 1)
        self.mock_server.wait_for_message.assert_called_with("/test/command", 2.0)
        self.assertEqual(result, 42)

        # Test with custom response address
        result = self.controller.send_and_wait("/test/command", 1, "/test/response")
        self.mock_server.wait_for_message.assert_called_with("/test/response", 2.0)

    def test_get_track_info(self):
        """Test retrieving track information"""
        # Set up mock track data
        self.mock_server.received_messages = {
            "/track/1/name": "Audio Track",
            "/track/1/volume": 64,
            "/track/1/pan": 64,
            "/track/1/mute": 0,
            "/track/1/solo": 0,
            "/track/2/name": "Other Track",  # Should be ignored
        }

        # Get track info
        track_info = self.controller.get_track_info(1)

        # Verify client refreshed
        self.mock_client.refresh.assert_called_once()

        # Verify track info extracted correctly
        self.assertEqual(track_info, {"name": "Audio Track", "volume": 64, "pan": 64, "mute": 0, "solo": 0})

    def test_get_device_params(self):
        """Test retrieving device parameters"""
        # Set up mock parameter data
        self.mock_server.received_messages = {
            "/device/param/1/exists": 1,
            "/device/param/1/name": "Cutoff",
            "/device/param/1/value": 64,
            "/device/param/2/exists": 1,
            "/device/param/2/name": "Resonance",
            "/device/param/2/value": 32,
            "/device/param/3/exists": 0,
        }

        # Mock get_message to return values from received_messages
        self.mock_server.get_message = lambda addr: self.mock_server.received_messages.get(addr)

        # Get device parameters
        params = self.controller.get_device_params()

        # Verify client refreshed
        self.mock_client.refresh.assert_called_once()

        # Verify parameters extracted correctly
        self.assertEqual(len(params), 2)
        self.assertEqual(params[0]["name"], "Cutoff")
        self.assertEqual(params[0]["value"], 64)
        self.assertEqual(params[1]["name"], "Resonance")
        self.assertEqual(params[1]["value"], 32)


if __name__ == "__main__":
    unittest.main()
