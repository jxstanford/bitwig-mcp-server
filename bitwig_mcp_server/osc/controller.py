"""
Bitwig OSC Controller

High-level controller that combines client and server functionality
"""

import logging
import time
from typing import Any, Optional

from .client import BitwigOSCClient
from .server import BitwigOSCServer

logger = logging.getLogger(__name__)


class BitwigOSCController:
    """Controller for bidirectional OSC communication with Bitwig Studio"""

    def __init__(self, ip: str = "127.0.0.1", send_port: int = 8000, receive_port: int = 9000):
        """Initialize the controller

        Args:
            ip: IP address of Bitwig instance
            send_port: Port to send messages to
            receive_port: Port to receive messages on
        """
        self.client = BitwigOSCClient(ip, send_port)
        self.server = BitwigOSCServer(ip, receive_port)
        self.ready = False

    def start(self) -> None:
        """Start the controller"""
        self.server.start()
        # Wait briefly for server to start
        time.sleep(0.1)

        # Request initial state from Bitwig
        self.client.refresh()

        # Wait for initial response
        time.sleep(0.5)
        self.ready = True

    def stop(self) -> None:
        """Stop the controller"""
        self.server.stop()

    def __enter__(self) -> "BitwigOSCController":
        """Context manager entry"""
        self.start()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit"""
        self.stop()

    # Synchronized command methods with response waiting
    def send_and_wait(
        self, address: str, value: Any, response_address: Optional[str] = None, timeout: float = 2.0
    ) -> Optional[Any]:
        """Send command and wait for response

        Args:
            address: The OSC address to send to
            value: The value to send
            response_address: The address to wait for (defaults to same as sent)
            timeout: Timeout in seconds

        Returns:
            The response value, or None if timeout occurred
        """
        if response_address is None:
            response_address = address

        # Clear any previous messages with this address
        self.server.received_messages.pop(response_address, None)

        # Send the command
        self.client.send(address, value)

        # Wait for response
        return self.server.wait_for_message(response_address, timeout)

    # High-level control methods
    def get_track_info(self, track_index: int) -> dict[str, Any]:
        """Get information about a track

        Args:
            track_index: Track index (1-based)

        Returns:
            Dict containing track information
        """
        # Refresh to get latest state
        self.client.refresh()
        time.sleep(0.5)

        prefix = f"/track/{track_index}/"
        track_info = {}

        # Extract all track properties from received messages
        for address, value in self.server.received_messages.items():
            if address.startswith(prefix):
                # Extract property name from address
                prop = address[len(prefix) :]
                track_info[prop] = value

        return track_info

    def get_device_params(self) -> list[dict[str, Any]]:
        """Get information about device parameters

        Returns:
            List of parameter information dictionaries
        """
        # Refresh to get latest state
        self.client.refresh()
        time.sleep(0.5)

        params = []

        # Find all parameters
        for i in range(1, 9):  # Assuming 8 parameters max
            prefix = f"/device/param/{i}/"
            param_info = {}

            # Check if parameter exists
            exists = self.server.get_message(f"{prefix}exists")
            if not exists:
                continue

            # Extract parameter properties
            for address, value in self.server.received_messages.items():
                if address.startswith(prefix):
                    # Extract property name from address
                    prop = address[len(prefix) :]
                    param_info[prop] = value

            params.append(param_info)

        return params
