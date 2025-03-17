"""
Bitwig OSC Client

Handles communication with Bitwig Studio via OSC
"""

import logging
from typing import Any, Optional

from pythonosc import udp_client

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
        """
        self.client = udp_client.SimpleUDPClient(ip, port)
        self.addr_log: list[str] = []  # Log of sent addresses for verification

    def send(self, address: str, value: Any) -> None:
        """Send an OSC message to Bitwig

        Args:
            address: The OSC address to send to
            value: The value to send
        """
        logger.debug(f"Sending: {address} = {value}")
        self.client.send_message(address, value)
        self.addr_log.append(address)

    def get_sent_addresses(self) -> list[str]:
        """Get list of addresses that were sent

        Returns:
            List of OSC addresses that have been sent
        """
        return self.addr_log

    def refresh(self) -> None:
        """Request a refresh of all values from Bitwig"""
        self.send("/refresh", 1)

    # Transport controls
    def play(self, state: Optional[bool] = None) -> None:
        """Control playback

        Args:
            state: True to play, False to stop, None to toggle
        """
        if state is None:
            self.send("/play", None)  # Toggle
        else:
            self.send("/play", 1 if state else 0)

    def stop(self) -> None:
        """Stop playback"""
        self.send("/stop", 1)

    def set_tempo(self, bpm: float) -> None:
        """Set the tempo

        Args:
            bpm: Tempo in beats per minute (0-666)
        """
        if not 0 <= bpm <= 666:
            logger.warning(f"Tempo {bpm} outside valid range (0-666), clamping")
            bpm = max(0, min(666, bpm))
        self.send("/tempo/raw", bpm)

    # Track controls
    def set_track_volume(self, track_index: int, volume: float) -> None:
        """Set track volume

        Args:
            track_index: Track index (1-based)
            volume: Volume value (0-128)
        """
        MAX_VALUE = 128
        if not 0 <= volume <= MAX_VALUE:
            logger.warning(f"Volume {volume} outside valid range (0-{MAX_VALUE}), clamping")
            volume = max(0, min(MAX_VALUE, volume))
        self.send(f"/track/{track_index}/volume", volume)

    def set_track_pan(self, track_index: int, pan: float) -> None:
        """Set track pan

        Args:
            track_index: Track index (1-based)
            pan: Pan value (0-128), with 64 being center
        """
        MAX_VALUE = 128
        if not 0 <= pan <= MAX_VALUE:
            logger.warning(f"Pan {pan} outside valid range (0-{MAX_VALUE}), clamping")
            pan = max(0, min(MAX_VALUE, pan))
        self.send(f"/track/{track_index}/pan", pan)

    def toggle_track_mute(self, track_index: int) -> None:
        """Toggle track mute state

        Args:
            track_index: Track index (1-based)
        """
        self.send(f"/track/{track_index}/mute", None)

    def set_track_mute(self, track_index: int, mute: bool) -> None:
        """Set track mute state

        Args:
            track_index: Track index (1-based)
            mute: True to mute, False to unmute
        """
        self.send(f"/track/{track_index}/mute", 1 if mute else 0)

    # Device controls
    def set_device_parameter(self, param_index: int, value: float) -> None:
        """Set device parameter value

        Args:
            param_index: Parameter index (1-based)
            value: Parameter value (0-128)
        """
        MAX_VALUE = 128
        if not 0 <= value <= MAX_VALUE:
            logger.warning(f"Parameter value {value} outside valid range (0-{MAX_VALUE}), clamping")
            value = max(0, min(MAX_VALUE, value))
        self.send(f"/device/param/{param_index}/value", value)
