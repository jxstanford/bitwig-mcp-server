"""
Bitwig OSC Server

Listens for OSC messages from Bitwig
"""

import logging
import threading
import time
from datetime import datetime
from typing import Any, Callable, Optional

from pythonosc import dispatcher
from pythonosc.osc_server import ThreadingOSCUDPServer

logger = logging.getLogger(__name__)

# Default OSC settings
DEFAULT_BITWIG_IP = "127.0.0.1"
DEFAULT_RECEIVE_PORT = 9000  # Port we listen on


class BitwigOSCServer:
    """Server for receiving OSC messages from Bitwig Studio"""

    def __init__(
        self,
        ip: str = DEFAULT_BITWIG_IP,
        port: int = DEFAULT_RECEIVE_PORT,
        message_handler: Optional[Callable[[str, Any], None]] = None,
    ):
        """Initialize the OSC server

        Args:
            ip: The IP address to listen on
            port: The port to listen on
            message_handler: Optional handler for all messages
        """
        self.ip = ip
        self.port = port
        self.running = False
        self.received_messages: dict[str, Any] = {}
        self.server: Optional[ThreadingOSCUDPServer] = None
        self.server_thread: Optional[threading.Thread] = None

        # Set up dispatcher
        self.dispatcher = dispatcher.Dispatcher()

        # If a custom handler was provided, wrap it
        if message_handler:
            self.external_handler = message_handler
            self.dispatcher.set_default_handler(self._handler_wrapper)
        else:
            self.external_handler = None
            self.dispatcher.set_default_handler(self._default_handler)

    def _handler_wrapper(self, address: str, *args: Any) -> None:
        """Wrapper for external handler that also stores messages"""
        self._default_handler(address, *args)
        if self.external_handler:
            self.external_handler(address, *args)

    def _default_handler(self, address: str, *args: Any) -> None:
        """Default handler for all OSC messages from Bitwig"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

        # Store the received message for later retrieval
        if args and len(args) > 0:
            value = args[0]
            self.received_messages[address] = value
            logger.debug(f"[{timestamp}] Received: {address} = {value}")
        else:
            self.received_messages[address] = None
            logger.debug(f"[{timestamp}] Received: {address} (no value)")

    def start(self) -> None:
        """Start the OSC server"""
        if self.running:
            logger.warning("Server already running")
            return

        # Create and start the server in a new thread
        self.server = ThreadingOSCUDPServer((self.ip, self.port), self.dispatcher)
        logger.info(f"OSC Server listening on {self.ip}:{self.port}")

        # Set running flag
        self.running = True

        # Start server thread
        self.server_thread = threading.Thread(target=self._server_loop)
        self.server_thread.daemon = True
        self.server_thread.start()

    def _server_loop(self) -> None:
        """Server thread function"""
        while self.running and self.server:
            self.server.handle_request()

    def stop(self) -> None:
        """Stop the OSC server"""
        if not self.running:
            return

        logger.info("Shutting down OSC server...")
        self.running = False

        # Server should exit on next handle_request
        if self.server_thread:
            self.server_thread.join(timeout=1.0)

    def get_message(self, address: str) -> Optional[Any]:
        """Get the latest message value for an address

        Args:
            address: The OSC address

        Returns:
            The value, or None if not received
        """
        return self.received_messages.get(address)

    def wait_for_message(self, address: str, timeout: float = 3.0) -> Optional[Any]:
        """Wait for a specific message to be received

        Args:
            address: The OSC address to wait for
            timeout: Maximum time to wait in seconds

        Returns:
            The message value, or None if timeout occurred
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            if address in self.received_messages:
                return self.received_messages[address]
            time.sleep(0.1)
        return None

    def clear_messages(self) -> None:
        """Clear all stored messages"""
        self.received_messages.clear()
