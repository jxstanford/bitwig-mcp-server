"""
Bitwig OSC Client

Handles communication with Bitwig Studio via OSC
"""

import logging
import socket
from typing import Any, Dict, List, Optional

from pythonosc import udp_client

from .exceptions import (
    ConnectionError,
    InvalidParameterError,
)

logger = logging.getLogger(__name__)

# Default OSC settings (matching Bitwig/git-moss defaults)
DEFAULT_BITWIG_IP = "127.0.0.1"
DEFAULT_SEND_PORT = 8000  # Port Bitwig listens on


class BitwigOSCClient:
    """Client for sending OSC messages to Bitwig Studio"""

    def __init__(self, ip: str = DEFAULT_BITWIG_IP, port: int = DEFAULT_SEND_PORT):
        """Initialize the OSC client

        Args:
            ip: The IP address of the Bitwig instance
            port: The port Bitwig is listening on for OSC messages

        Raises:
            ConnectionError: If unable to create the UDP client
        """
        try:
            self.ip = ip
            self.port = port
            self.client = udp_client.SimpleUDPClient(ip, port)
            self.addr_log: List[str] = []  # Log of sent addresses for verification
        except socket.error as e:
            raise ConnectionError(details=f"Failed to create UDP client: {e}")
        except Exception as e:
            raise ConnectionError(details=str(e))

    def send(self, address: str, value: Any) -> None:
        """Send an OSC message to Bitwig

        Args:
            address: The OSC address to send to
            value: The value to send

        Raises:
            ConnectionError: If unable to send the message
        """
        try:
            logger.debug(f"Sending: {address} = {value}")
            self.client.send_message(address, value)
            self.addr_log.append(address)
        except socket.error as e:
            raise ConnectionError(details=f"Failed to send message to {address}: {e}")
        except Exception as e:
            raise ConnectionError(details=f"Error sending message to {address}: {e}")

    def get_sent_addresses(self) -> List[str]:
        """Get list of addresses that were sent

        Returns:
            List of OSC addresses that have been sent
        """
        return self.addr_log

    def refresh(self) -> None:
        """Request a refresh of all values from Bitwig

        Raises:
            ConnectionError: If unable to send the refresh command
        """
        self.send("/refresh", 1)

    # Transport controls
    def play(self, state: Optional[bool] = None) -> None:
        """Control playback

        Args:
            state: True to play, False to stop, None to toggle

        Raises:
            ConnectionError: If unable to send the command
        """
        if state is None:
            self.send("/play", None)  # Toggle
        else:
            self.send("/play", 1 if state else 0)

    def stop(self) -> None:
        """Stop playback

        Raises:
            ConnectionError: If unable to send the command
        """
        self.send("/stop", 1)

    def set_tempo(self, bpm: float) -> None:
        """Set the tempo

        Args:
            bpm: Tempo in beats per minute (20-999)

        Raises:
            InvalidParameterError: If bpm is not a number
            ConnectionError: If unable to send the command
        """
        # Tempo range is effectively 20-999 in Bitwig
        if not isinstance(bpm, (int, float)):
            raise InvalidParameterError("bpm", bpm, "must be a number")

        # Give a wider range than Bitwig accepts to allow for clamping
        MAX_TEMPO = 999
        MIN_TEMPO = 20

        if bpm < MIN_TEMPO:
            logger.warning(f"Tempo {bpm} below minimum ({MIN_TEMPO}), clamping")
            bpm = MIN_TEMPO
        elif bpm > MAX_TEMPO:
            logger.warning(f"Tempo {bpm} above maximum ({MAX_TEMPO}), clamping")
            bpm = MAX_TEMPO

        self.send("/tempo/raw", bpm)

    # Track controls
    def set_track_volume(self, track_index: int, volume: float) -> None:
        """Set track volume

        Args:
            track_index: Track index (1-based)
            volume: Volume value (0-128, where 64 is 0dB)

        Raises:
            InvalidParameterError: If parameters are invalid
            ConnectionError: If unable to send the command
        """
        if not isinstance(track_index, int):
            raise InvalidParameterError(
                "track_index", track_index, "must be an integer"
            )

        if track_index < 1:
            raise InvalidParameterError(
                "track_index", track_index, "must be at least 1 (1-based indexing)"
            )

        MAX_VALUE = 128
        MIN_VALUE = 0

        if not isinstance(volume, (int, float)):
            raise InvalidParameterError("volume", volume, "must be a number")

        if volume < MIN_VALUE:
            logger.warning(f"Volume {volume} below minimum ({MIN_VALUE}), clamping")
            volume = MIN_VALUE
        elif volume > MAX_VALUE:
            logger.warning(f"Volume {volume} above maximum ({MAX_VALUE}), clamping")
            volume = MAX_VALUE

        self.send(f"/track/{track_index}/volume", volume)

    def set_track_pan(self, track_index: int, pan: float) -> None:
        """Set track pan

        Args:
            track_index: Track index (1-based)
            pan: Pan value (0-128, where 64 is center)

        Raises:
            InvalidParameterError: If parameters are invalid
            ConnectionError: If unable to send the command
        """
        if not isinstance(track_index, int):
            raise InvalidParameterError(
                "track_index", track_index, "must be an integer"
            )

        if track_index < 1:
            raise InvalidParameterError(
                "track_index", track_index, "must be at least 1 (1-based indexing)"
            )

        MAX_VALUE = 128
        MIN_VALUE = 0

        if not isinstance(pan, (int, float)):
            raise InvalidParameterError("pan", pan, "must be a number")

        if pan < MIN_VALUE:
            logger.warning(
                f"Pan {pan} below minimum ({MIN_VALUE}), clamping to left extreme"
            )
            pan = MIN_VALUE
        elif pan > MAX_VALUE:
            logger.warning(
                f"Pan {pan} above maximum ({MAX_VALUE}), clamping to right extreme"
            )
            pan = MAX_VALUE

        self.send(f"/track/{track_index}/pan", pan)

    def toggle_track_mute(self, track_index: int) -> None:
        """Toggle track mute state

        Args:
            track_index: Track index (1-based)

        Raises:
            InvalidParameterError: If track_index is invalid
            ConnectionError: If unable to send the command
        """
        if not isinstance(track_index, int):
            raise InvalidParameterError(
                "track_index", track_index, "must be an integer"
            )

        if track_index < 1:
            raise InvalidParameterError(
                "track_index", track_index, "must be at least 1 (1-based indexing)"
            )

        self.send(f"/track/{track_index}/mute", None)

    def set_track_mute(self, track_index: int, mute: bool) -> None:
        """Set track mute state

        Args:
            track_index: Track index (1-based)
            mute: True to mute, False to unmute

        Raises:
            InvalidParameterError: If parameters are invalid
            ConnectionError: If unable to send the command
        """
        if not isinstance(track_index, int):
            raise InvalidParameterError(
                "track_index", track_index, "must be an integer"
            )

        if track_index < 1:
            raise InvalidParameterError(
                "track_index", track_index, "must be at least 1 (1-based indexing)"
            )

        if not isinstance(mute, bool):
            raise InvalidParameterError("mute", mute, "must be a boolean")

        self.send(f"/track/{track_index}/mute", 1 if mute else 0)

    # Device controls
    def set_device_parameter(self, param_index: int, value: float) -> None:
        """Set device parameter value

        Args:
            param_index: Parameter index (1-based)
            value: Parameter value (0-128)

        Raises:
            InvalidParameterError: If parameters are invalid
            ConnectionError: If unable to send the command
        """
        if not isinstance(param_index, int):
            raise InvalidParameterError(
                "param_index", param_index, "must be an integer"
            )

        if param_index < 1:
            raise InvalidParameterError(
                "param_index", param_index, "must be at least 1 (1-based indexing)"
            )

        if param_index > 8:
            raise InvalidParameterError("param_index", param_index, "must be at most 8")

        MAX_VALUE = 128
        MIN_VALUE = 0

        if not isinstance(value, (int, float)):
            raise InvalidParameterError("value", value, "must be a number")

        if value < MIN_VALUE:
            logger.warning(
                f"Parameter value {value} below minimum ({MIN_VALUE}), clamping"
            )
            value = MIN_VALUE
        elif value > MAX_VALUE:
            logger.warning(
                f"Parameter value {value} above maximum ({MAX_VALUE}), clamping"
            )
            value = MAX_VALUE

        self.send(f"/device/param/{param_index}/value", value)

    def toggle_device_bypass(self) -> None:
        """Toggle bypass state of the currently selected device

        Raises:
            ConnectionError: If unable to send the command
        """
        self.send("/device/bypass", None)

    def select_device_sibling(self, sibling_index: int) -> None:
        """Select a sibling device (in the same chain as current device)

        Args:
            sibling_index: Index of the sibling device (1-8)

        Raises:
            InvalidParameterError: If sibling_index is invalid
            ConnectionError: If unable to send the command
        """
        if not isinstance(sibling_index, int):
            raise InvalidParameterError(
                "sibling_index", sibling_index, "must be an integer"
            )

        if sibling_index < 1 or sibling_index > 8:
            raise InvalidParameterError(
                "sibling_index", sibling_index, "must be between 1 and 8"
            )

        self.send(f"/device/sibling/{sibling_index}/select", 1)

    def navigate_device(self, direction: str) -> None:
        """Navigate to next/previous device

        Args:
            direction: Navigation direction, either "next" or "previous"

        Raises:
            InvalidParameterError: If direction is invalid
            ConnectionError: If unable to send the command
        """
        if direction not in ["next", "previous"]:
            raise InvalidParameterError(
                "direction", direction, "must be either 'next' or 'previous'"
            )

        # Map to OSC command
        nav_symbol = "+" if direction == "next" else "-"
        self.send(f"/device/{nav_symbol}", None)

    def enter_device_layer(self, layer_index: int) -> None:
        """Enter a device layer/chain

        Args:
            layer_index: Index of the layer to enter (1-8)

        Raises:
            InvalidParameterError: If layer_index is invalid
            ConnectionError: If unable to send the command
        """
        if not isinstance(layer_index, int):
            raise InvalidParameterError(
                "layer_index", layer_index, "must be an integer"
            )

        if layer_index < 1 or layer_index > 8:
            raise InvalidParameterError(
                "layer_index", layer_index, "must be between 1 and 8"
            )

        self.send(f"/device/layer/{layer_index}/enter", None)

    def exit_device_layer(self) -> None:
        """Exit current device layer (go to parent)

        Raises:
            ConnectionError: If unable to send the command
        """
        self.send("/device/layer/parent", None)

    def toggle_device_window(self) -> None:
        """Toggle device window visibility

        Raises:
            ConnectionError: If unable to send the command
        """
        self.send("/device/window", None)

    def select_device_by_index(self, device_index: int) -> None:
        """Select a device by its index

        Args:
            device_index: Index of the device to select (1-based)

        Raises:
            InvalidParameterError: If device_index is invalid
            ConnectionError: If unable to send the command
        """
        if not isinstance(device_index, int):
            raise InvalidParameterError(
                "device_index", device_index, "must be an integer"
            )

        if device_index < 1:
            raise InvalidParameterError(
                "device_index", device_index, "must be at least 1 (1-based indexing)"
            )

        self.send(f"/device/select/{device_index}", 1)

    # Browser controls based on OSC documentation
    def browse_for_device(self, position: str = "after") -> None:
        """Activate browser to insert a device

        Args:
            position: Where to insert the device ("after" or "before" the selected device)

        Raises:
            InvalidParameterError: If position is invalid
            ConnectionError: If unable to send the command
        """
        if position not in ["after", "before"]:
            raise InvalidParameterError(
                "position", position, "must be either 'after' or 'before'"
            )

        if position == "after":
            self.send("/browser/device", None)
        else:
            self.send("/browser/device/before", None)

    def browse_for_preset(self) -> None:
        """Activate browser to browse for presets of currently selected device

        Raises:
            ConnectionError: If unable to send the command
        """
        self.send("/browser/preset", None)

    def commit_browser_selection(self) -> None:
        """Commit the current selection in the browser

        Raises:
            ConnectionError: If unable to send the command
        """
        self.send("/browser/commit", None)

    def cancel_browser(self) -> None:
        """Cancel the current browser session

        Raises:
            ConnectionError: If unable to send the command
        """
        self.send("/browser/cancel", None)

    def navigate_browser_tab(self, direction: str) -> None:
        """Navigate between browser tabs

        Args:
            direction: Direction to navigate ("+", "-")

        Raises:
            InvalidParameterError: If direction is invalid
            ConnectionError: If unable to send the command
        """
        if direction not in ["+", "-"]:
            raise InvalidParameterError(
                "direction", direction, "must be either '+' or '-'"
            )

        self.send(f"/browser/tab/{direction}", None)

    def navigate_browser_filter(self, filter_index: int, direction: str) -> None:
        """Navigate through filter options

        Args:
            filter_index: Index of the filter column (1-6)
            direction: Direction to navigate ("+", "-")

        Raises:
            InvalidParameterError: If parameters are invalid
            ConnectionError: If unable to send the command
        """
        if not isinstance(filter_index, int) or filter_index < 1 or filter_index > 6:
            raise InvalidParameterError(
                "filter_index", filter_index, "must be between 1 and 6"
            )

        if direction not in ["+", "-"]:
            raise InvalidParameterError(
                "direction", direction, "must be either '+' or '-'"
            )

        self.send(f"/browser/filter/{filter_index}/{direction}", None)

    def reset_browser_filter(self, filter_index: int) -> None:
        """Reset a browser filter

        Args:
            filter_index: Index of the filter column to reset (1-6)

        Raises:
            InvalidParameterError: If filter_index is invalid
            ConnectionError: If unable to send the command
        """
        if not isinstance(filter_index, int) or filter_index < 1 or filter_index > 6:
            raise InvalidParameterError(
                "filter_index", filter_index, "must be between 1 and 6"
            )

        self.send(f"/browser/filter/{filter_index}/reset", None)

    def navigate_browser_result(self, direction: str) -> None:
        """Navigate through browser results

        Args:
            direction: Direction to navigate ("+", "-")

        Raises:
            InvalidParameterError: If direction is invalid
            ConnectionError: If unable to send the command
        """
        if direction not in ["+", "-"]:
            raise InvalidParameterError(
                "direction", direction, "must be either '+' or '-'"
            )

        self.send(f"/browser/result/{direction}", None)

    def navigate_browser_result_page(self, direction: str) -> None:
        """Navigate through browser result pages (each page contains up to 16 results)

        Args:
            direction: Direction to navigate ("+", "-")

        Raises:
            InvalidParameterError: If direction is invalid
            ConnectionError: If unable to send the command
        """
        if direction not in ["+", "-"]:
            raise InvalidParameterError(
                "direction", direction, "must be either '+' or '-'"
            )

        # Page navigation addresses based on DrivenByMoss implementation
        self.send(f"/browser/result/page/{direction}", None)

    # Higher-level convenience methods for common tasks
    def insert_device_after_selected(self) -> None:
        """Open browser to insert a device after the currently selected one

        Raises:
            ConnectionError: If unable to send the command
        """
        self.browse_for_device("after")

    def insert_device_before_selected(self) -> None:
        """Open browser to insert a device before the currently selected one

        Raises:
            ConnectionError: If unable to send the command
        """
        self.browse_for_device("before")

    def browse_device_presets(self) -> None:
        """Open browser to browse presets for the currently selected device

        Raises:
            ConnectionError: If unable to send the command
        """
        self.browse_for_preset()

    def select_next_browser_tab(self) -> None:
        """Select the next browser tab

        Raises:
            ConnectionError: If unable to send the command
        """
        self.navigate_browser_tab("+")

    def select_previous_browser_tab(self) -> None:
        """Select the previous browser tab

        Raises:
            ConnectionError: If unable to send the command
        """
        self.navigate_browser_tab("-")

    def select_next_filter_option(self, filter_index: int) -> None:
        """Select the next option in a filter column

        Args:
            filter_index: Index of the filter column (1-6)

        Raises:
            InvalidParameterError: If filter_index is invalid
            ConnectionError: If unable to send the command
        """
        self.navigate_browser_filter(filter_index, "+")

    def select_previous_filter_option(self, filter_index: int) -> None:
        """Select the previous option in a filter column

        Args:
            filter_index: Index of the filter column (1-6)

        Raises:
            InvalidParameterError: If filter_index is invalid
            ConnectionError: If unable to send the command
        """
        self.navigate_browser_filter(filter_index, "-")

    def select_next_browser_result(self) -> None:
        """Select the next result in the browser

        Raises:
            ConnectionError: If unable to send the command
        """
        self.navigate_browser_result("+")

    def select_previous_browser_result(self) -> None:
        """Select the previous result in the browser

        Raises:
            ConnectionError: If unable to send the command
        """
        self.navigate_browser_result("-")

    def select_next_browser_result_page(self) -> None:
        """Navigate to the next page of browser results (up to 16 results per page)

        Raises:
            ConnectionError: If unable to send the command
        """
        self.navigate_browser_result_page("+")

    def select_previous_browser_result_page(self) -> None:
        """Navigate to the previous page of browser results (up to 16 results per page)

        Raises:
            ConnectionError: If unable to send the command
        """
        self.navigate_browser_result_page("-")

    # Workflow helper methods
    def browse_and_insert_device(
        self, num_tabs: int = 0, num_filters: List[int] = None, num_results: int = 0
    ) -> None:
        """Browse and insert a device using navigation commands

        Args:
            num_tabs: Number of tab navigations (positive = forward, negative = backward)
            num_filters: List of filter navigations by column index (e.g., [(1, 2), (4, -1)])
                        Format: List of tuples (filter_index, num_navigations)
            num_results: Number of result navigations (positive = forward, negative = backward)

        Raises:
            ConnectionError: If unable to send commands
        """
        # Open device browser
        self.browse_for_device("after")

        # Navigate to desired tab
        for _ in range(abs(num_tabs)):
            direction = "+" if num_tabs >= 0 else "-"
            self.navigate_browser_tab(direction)

        # Apply filter selections
        if num_filters:
            for filter_index, num_navigations in num_filters:
                for _ in range(abs(num_navigations)):
                    direction = "+" if num_navigations >= 0 else "-"
                    self.navigate_browser_filter(filter_index, direction)

        # Navigate to desired result
        for _ in range(abs(num_results)):
            direction = "+" if num_results >= 0 else "-"
            self.navigate_browser_result(direction)

        # Commit selection
        self.commit_browser_selection()

    def browse_and_load_preset(
        self, num_filters: List[int] = None, num_results: int = 0
    ) -> None:
        """Browse and load a preset using navigation commands

        Args:
            num_filters: List of filter navigations by column index (e.g., [(1, 2), (4, -1)])
                        Format: List of tuples (filter_index, num_navigations)
            num_results: Number of result navigations (positive = forward, negative = backward)

        Raises:
            ConnectionError: If unable to send commands
        """
        # Open preset browser
        self.browse_for_preset()

        # Apply filter selections
        if num_filters:
            for filter_index, num_navigations in num_filters:
                for _ in range(abs(num_navigations)):
                    direction = "+" if num_navigations >= 0 else "-"
                    self.navigate_browser_filter(filter_index, direction)

        # Navigate to desired result
        for _ in range(abs(num_results)):
            direction = "+" if num_results >= 0 else "-"
            self.navigate_browser_result(direction)

        # Commit selection
        self.commit_browser_selection()

    def get_status(self) -> Dict[str, Any]:
        """Get client status information

        Returns:
            Dict with status information
        """
        return {
            "ip": self.ip,
            "port": self.port,
            "messages_sent": len(self.addr_log),
            "last_addresses": self.addr_log[-5:] if self.addr_log else [],
        }
