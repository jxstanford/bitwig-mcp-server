"""
Bitwig OSC Controller

High-level controller that combines client and server functionality
"""

import logging
import socket
import time
from typing import Any, Dict, List, Optional

from .client import BitwigOSCClient
from .error_handler import ErrorHandler
from .exceptions import (
    BitwigNotRespondingError,
    ConnectionError,
    ResourceNotFoundError,
    TimeoutError,
)
from .server import BitwigOSCServer

logger = logging.getLogger(__name__)


class BitwigOSCController:
    """Controller for bidirectional OSC communication with Bitwig Studio"""

    def __init__(
        self,
        ip: str = "127.0.0.1",
        send_port: int = 8000,
        receive_port: int = 9000,
        connection_timeout: float = 5.0,
        reconnect_attempts: int = 3,
    ):
        """Initialize the controller

        Args:
            ip: IP address of Bitwig instance
            send_port: Port to send messages to
            receive_port: Port to receive messages on
            connection_timeout: Timeout for initial connection in seconds
            reconnect_attempts: Number of reconnection attempts
        """
        self.ip = ip
        self.send_port = send_port
        self.receive_port = receive_port
        self.connection_timeout = connection_timeout
        self.reconnect_attempts = reconnect_attempts

        # Create client and server
        self.client = BitwigOSCClient(ip, send_port)
        self.server = BitwigOSCServer(ip, receive_port)

        # Create error handler
        self.error_handler = ErrorHandler()

        # Controller state
        self.ready = False
        self.connected = False
        self.last_refresh = 0.0
        self.connection_attempts = 0

    def start(self) -> None:
        """Start the controller

        Raises:
            ConnectionError: If unable to connect to Bitwig
        """
        try:
            # Start the OSC server
            self.server.start()

            # Wait briefly for server to start
            time.sleep(0.1)

            # Try to connect to Bitwig with timeout
            self._connect_with_timeout()

            # Mark as ready
            self.ready = True
            self.connected = True
            self.connection_attempts = 0
            self.error_handler.record_success()

            logger.info(
                f"OSC controller connected to Bitwig at {self.ip}:{self.send_port}"
            )

        except Exception as e:
            self.ready = False
            self.connected = False

            # Clean up
            try:
                self.server.stop()
            except Exception:
                pass

            error = ConnectionError(details=str(e))
            self.error_handler.record_error("start", error)
            raise error

    def _connect_with_timeout(self) -> None:
        """Attempt to connect to Bitwig with timeout

        Raises:
            ConnectionError: If unable to connect to Bitwig
            TimeoutError: If connection times out
        """
        start_time = time.time()
        self.connection_attempts += 1

        # Send ping to check if Bitwig is responding
        try:
            # Request initial state from Bitwig
            self.client.refresh()

            # Wait for a response with timeout
            while time.time() - start_time < self.connection_timeout:
                # Check if we've received any messages
                if self.server.received_messages:
                    return

                # Wait a bit before checking again
                time.sleep(0.1)

            # If we get here, we timed out
            if self.connection_attempts < self.reconnect_attempts:
                logger.warning(
                    f"Connection attempt {self.connection_attempts} timed out, retrying..."
                )
                return self._connect_with_timeout()

            raise TimeoutError("connect", self.connection_timeout)

        except socket.error as e:
            raise ConnectionError(details=f"Socket error: {e}")
        except Exception as e:
            raise ConnectionError(details=str(e))

    def stop(self) -> None:
        """Stop the controller"""
        self.ready = False
        self.connected = False
        self.server.stop()
        logger.info("OSC controller stopped")

    def __enter__(self) -> "BitwigOSCController":
        """Context manager entry"""
        self.start()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit"""
        self.stop()

    def ping(self, timeout: float = 2.0) -> bool:
        """Check if Bitwig is responding

        Args:
            timeout: Timeout in seconds

        Returns:
            True if Bitwig is responding, False otherwise
        """
        try:
            # Clear all messages
            self.server.clear_messages()

            # Send a query that should always return a value
            self.client.send("/refresh", 1)

            # Wait for any response
            start_time = time.time()
            while time.time() - start_time < timeout:
                if self.server.received_messages:
                    self.error_handler.record_success()
                    return True
                time.sleep(0.1)

            # If we get here, we timed out
            error = BitwigNotRespondingError()
            self.error_handler.record_error("ping", error)
            return False

        except Exception as e:
            logger.error(f"Error pinging Bitwig: {e}")
            return False

    def refresh(self, timeout: float = 2.0) -> bool:
        """Refresh state from Bitwig

        Args:
            timeout: Timeout in seconds

        Returns:
            True if successful, False otherwise
        """
        try:
            # Rate limit refreshes
            now = time.time()
            if (
                now - self.last_refresh < 0.2
            ):  # Don't refresh more than 5 times per second
                return True

            self.last_refresh = now

            # Send refresh command
            self.client.refresh()

            # Wait for any response
            start_time = time.time()
            received_count = len(self.server.received_messages)

            # Wait for new messages
            while time.time() - start_time < timeout:
                # If we've received new messages, success
                if len(self.server.received_messages) > received_count:
                    logger.debug(
                        f"Received {len(self.server.received_messages) - received_count} new messages during refresh"
                    )
                    self.error_handler.record_success()
                    return True
                time.sleep(0.1)

            # If we get here, we timed out waiting for new messages
            logger.debug(
                f"No new messages received after {timeout}s. Testing connection..."
            )

            # Explicitly test connection with a ping
            if self.ping(timeout=1.0):
                # Connection is good, Bitwig just didn't send new messages
                # This can happen when Bitwig has already sent all the state info
                # and doesn't have anything new to report
                logger.info(
                    "No new messages from Bitwig, but connection is good. Proceeding with cached state."
                )
                self.error_handler.record_success()
                return True

            # Connection test failed - we have a real problem
            logger.warning("Connection test failed after refresh timeout")
            if self.error_handler.connection_status["consecutive_timeouts"] > 3:
                error = BitwigNotRespondingError()
                self.error_handler.record_error("refresh", error)
                self.connected = False

            return False

        except Exception as e:
            logger.error(f"Error refreshing Bitwig state: {e}")
            return False

    # Synchronized command methods with response waiting
    def send_and_wait(
        self,
        address: str,
        value: Any,
        response_address: Optional[str] = None,
        timeout: float = 2.0,
    ) -> Any:
        """Send command and wait for response

        Args:
            address: The OSC address to send to
            value: The value to send
            response_address: The address to wait for (defaults to same as sent)
            timeout: Timeout in seconds

        Returns:
            The response value

        Raises:
            TimeoutError: If the operation times out
            BitwigNotRespondingError: If Bitwig is not responding
        """
        # Ensure connection is healthy
        if not self.ready or not self.connected:
            if not self._attempt_reconnect():
                raise BitwigNotRespondingError(address)

        if response_address is None:
            response_address = address

        # Define the operation to retry
        def _send_and_wait_operation():
            # Clear any previous messages with this address
            self.server.received_messages.pop(response_address, None)

            # Send the command
            self.client.send(address, value)

            # Wait for response
            result = self.server.wait_for_message(response_address, timeout)
            if result is None:
                raise TimeoutError(f"send_and_wait({address})", timeout)
            return result

        # Retry the operation with timeout handling
        try:
            return self.error_handler.retry_with_timeout(
                _send_and_wait_operation,
                f"send_and_wait({address})",
                max_retries=2,
                retry_delay=0.2,
                timeout=timeout,
            )
        except Exception:
            # If still failing after retries, check connection
            if not self.ping():
                self.connected = False
                raise BitwigNotRespondingError(address)
            raise

    def _attempt_reconnect(self) -> bool:
        """Attempt to reconnect to Bitwig

        Returns:
            True if successful, False otherwise
        """
        if self.connection_attempts >= self.reconnect_attempts:
            logger.error("Maximum reconnection attempts reached")
            return False

        logger.info("Attempting to reconnect to Bitwig...")

        try:
            # Stop everything
            try:
                self.server.stop()
            except Exception:
                pass

            time.sleep(1.0)

            # Restart
            self.server = BitwigOSCServer(self.ip, self.receive_port)
            self.server.start()

            # Attempt connection
            self._connect_with_timeout()

            self.ready = True
            self.connected = True
            self.error_handler.record_success()

            logger.info("Successfully reconnected to Bitwig")
            return True

        except Exception as e:
            logger.error(f"Failed to reconnect: {e}")
            return False

    # High-level control methods
    def get_track_info(self, track_index: int) -> Dict[str, Any]:
        """Get information about a track

        Args:
            track_index: Track index (1-based)

        Returns:
            Dict containing track information

        Raises:
            InvalidParameterError: If track_index is invalid
            ResourceNotFoundError: If track not found
            BitwigNotRespondingError: If Bitwig is not responding
        """
        # Validate track index
        track_index = self.error_handler.validate_track_index(track_index)

        # Refresh to get latest state
        if not self.refresh():
            raise BitwigNotRespondingError(f"/track/{track_index}")

        # Check if track exists
        name = self.server.get_message(f"/track/{track_index}/name")
        if not name:
            raise ResourceNotFoundError("Track", str(track_index))

        prefix = f"/track/{track_index}/"
        track_info = {"name": name, "index": track_index}

        # Extract all track properties from received messages
        for address, value in self.server.received_messages.items():
            if address.startswith(prefix) and not address.endswith("/name"):
                # Extract property name from address
                prop = address[len(prefix) :]
                track_info[prop] = value

        return track_info

    def get_device_params(self) -> List[Dict[str, Any]]:
        """Get information about device parameters

        Returns:
            List of parameter information dictionaries

        Raises:
            ResourceNotFoundError: If no device is selected
            BitwigNotRespondingError: If Bitwig is not responding
        """
        # Refresh to get latest state
        if not self.refresh():
            raise BitwigNotRespondingError("/device")

        # Check if a device is selected
        device_exists = self.server.get_message("/device/exists")
        if not device_exists:
            raise ResourceNotFoundError("Device", "No device selected")

        params = []

        # Find all parameters
        for i in range(1, 9):  # Assuming 8 parameters max
            prefix = f"/device/param/{i}/"
            param_exists = self.server.get_message(f"{prefix}exists")

            if not param_exists:
                continue

            param_info = {"index": i}

            # Extract parameter properties
            for address, value in self.server.received_messages.items():
                if address.startswith(prefix) and not address.endswith("/exists"):
                    # Extract property name from address
                    prop = address[len(prefix) :]
                    param_info[prop] = value

            # Only add if we have some properties
            if len(param_info) > 1:
                params.append(param_info)

        return params

    def get_status(self) -> Dict[str, Any]:
        """Get controller status information

        Returns:
            Dict with status information
        """
        connection_health = self.error_handler.check_connection_health()

        # If connection doesn't seem healthy but we think we're connected,
        # do a quick ping test
        if not connection_health and self.connected:
            self.connected = self.ping()

        return {
            "ready": self.ready,
            "connected": self.connected,
            "ip": self.ip,
            "send_port": self.send_port,
            "receive_port": self.receive_port,
            "connection_health": connection_health,
            "errors": self.error_handler.recent_errors,
            "diagnostics": self.error_handler.get_diagnostic_info(),
        }
