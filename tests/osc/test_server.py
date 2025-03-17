"""Tests for the BitwigOSCServer class"""

import unittest
from unittest.mock import MagicMock, patch

from bitwig_mcp_server.osc.server import BitwigOSCServer


class TestBitwigOSCServer(unittest.TestCase):
    """Test cases for BitwigOSCServer"""

    @patch("bitwig_mcp_server.osc.server.ThreadingOSCUDPServer")
    def setUp(self, mock_server_class):
        """Set up test environment"""
        self.mock_server = MagicMock()
        mock_server_class.return_value = self.mock_server

        self.server = BitwigOSCServer()
        self.custom_handler = MagicMock()

    def test_default_handler(self):
        """Test the default message handler"""
        # Test with a value
        self.server._default_handler("/test/address", 42)
        self.assertEqual(self.server.received_messages["/test/address"], 42)

        # Test without a value
        self.server._default_handler("/test/empty")
        self.assertIsNone(self.server.received_messages["/test/empty"])

    def test_custom_handler(self):
        """Test using a custom message handler"""
        # Create server with custom handler
        server = BitwigOSCServer(message_handler=self.custom_handler)

        # Test handler wrapper
        server._handler_wrapper("/test/address", 42)

        # Verify custom handler was called
        self.custom_handler.assert_called_once_with("/test/address", 42)

        # Verify message was stored
        self.assertEqual(server.received_messages["/test/address"], 42)

    def test_get_message(self):
        """Test retrieving messages"""
        self.server.received_messages["/test/address"] = 42

        # Test getting existing message
        self.assertEqual(self.server.get_message("/test/address"), 42)

        # Test getting non-existent message
        self.assertIsNone(self.server.get_message("/nonexistent"))

    def test_clear_messages(self):
        """Test clearing messages"""
        self.server.received_messages = {"/test/1": 1, "/test/2": 2}
        self.server.clear_messages()
        self.assertEqual(self.server.received_messages, {})

    @patch("bitwig_mcp_server.osc.server.ThreadingOSCUDPServer")
    def test_start_stop(self, mock_server_class):
        """Test starting and stopping server"""
        # Create mock server instance
        mock_server_instance = MagicMock()
        mock_server_class.return_value = mock_server_instance

        # Create mock thread
        thread_instance = MagicMock()
        with patch("threading.Thread", return_value=thread_instance):
            # Test starting
            self.server.start()
            self.assertTrue(self.server.running)
            mock_server_class.assert_called_once()

            # Test stopping
            self.server.stop()
            self.assertFalse(self.server.running)
            thread_instance.join.assert_called_once()


if __name__ == "__main__":
    unittest.main()
