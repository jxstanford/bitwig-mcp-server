"""
Bitwig OSC Integration Tests

This script tests communication with Bitwig Studio via OSC using the git-moss extension.
It uses pytest for more structured testing.

Requirements:
- python-osc library: pip install python-osc
- pytest: pip install pytest
- Bitwig Studio with git-moss OSC extension configured
"""

import threading
import time
from datetime import datetime

import pytest
from pythonosc import dispatcher, udp_client
from pythonosc.osc_server import ThreadingOSCUDPServer

# Default OSC settings (matching Bitwig/git-moss defaults)
DEFAULT_BITWIG_IP = "127.0.0.1"
DEFAULT_SEND_PORT = 8000  # Port Bitwig listens on
DEFAULT_RECEIVE_PORT = 9000  # Port we listen on

# Global flag to track if we're still running
running = True

# Messages received from Bitwig
received_messages = {}


@pytest.fixture(scope="module")
def client():
    """Create Bitwig OSC client"""
    client = BitwigOSCClient(DEFAULT_BITWIG_IP, DEFAULT_SEND_PORT)
    print(f"Initialized client sending to {DEFAULT_BITWIG_IP}:{DEFAULT_SEND_PORT}")

    # Initial refresh to get current state
    client.send("/refresh", 1)
    time.sleep(1)  # Give Bitwig time to respond

    return client


class BitwigOSCClient:
    """Client for sending OSC messages to Bitwig Studio"""

    def __init__(self, ip, port):
        self.client = udp_client.SimpleUDPClient(ip, port)
        self.addr_log = []  # Log of sent addresses for verification

    def send(self, address, value):
        """Send an OSC message to Bitwig"""
        print(f"Sending: {address} = {value}")
        self.client.send_message(address, value)
        self.addr_log.append(address)

    def get_sent_addresses(self):
        """Get list of addresses that were sent"""
        return self.addr_log


def generic_handler(address, *args):
    """Generic handler for all OSC messages from Bitwig"""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

    # Store the received message for later verification
    if args and len(args) > 0:
        value = args[0]
        received_messages[address] = value
        print(f"[{timestamp}] Received: {address} = {value}")
    else:
        received_messages[address] = None
        print(f"[{timestamp}] Received: {address} (no value)")


def server_loop(server):
    """Loop for serving OSC requests until program exits"""
    while running:
        server.handle_request()


def wait_for_response(address, timeout=3):
    """Wait for a response from Bitwig for the given address"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        if address in received_messages:
            return received_messages[address]
        time.sleep(0.1)
    return None


@pytest.fixture(scope="module")
def osc_listener():
    """Start the OSC server to receive messages from Bitwig"""
    # Create dispatcher for handling incoming messages
    disp = dispatcher.Dispatcher()

    # Register default handler for all addresses
    disp.set_default_handler(generic_handler)

    # Create and start the server in a new thread
    server = ThreadingOSCUDPServer((DEFAULT_BITWIG_IP, DEFAULT_RECEIVE_PORT), disp)
    print(f"OSC Server listening on {DEFAULT_BITWIG_IP}:{DEFAULT_RECEIVE_PORT}")

    # Serve until the global running flag is False
    server_thread = threading.Thread(target=server_loop, args=(server,))
    server_thread.daemon = True
    server_thread.start()

    # Yield the server instance
    yield server

    # Cleanup after tests
    global running
    running = False
    print("Shutting down OSC server...")
    time.sleep(0.5)  # Give server thread time to exit


@pytest.fixture(scope="module")
def ensure_device(client):
    """Attempt to add a device to the selected track if none exists"""
    # Refresh to get current state
    received_messages.clear()
    client.send("/refresh", 1)
    time.sleep(1.5)

    # Check if we already have a device
    device_exists = received_messages.get("/device/exists")
    if device_exists:
        print("Device already exists, using existing device")
        return True

    print("No device found, attempting to add EQ device to selected track...")

    # Check if there's a track selected
    track_selected = received_messages.get("/track/selected/exists")
    if not track_selected:
        print("No track is selected, cannot add device")
        return False

    # Try to add an EQ device
    client.send("/track/add/effect", 1)  # Generic add device command
    # Alternatively, try specific EQ command
    client.send("/eq/add", 1)
    time.sleep(2)

    # Refresh to check if device was added
    received_messages.clear()
    client.send("/refresh", 1)
    time.sleep(1.5)

    # Check again if we have a device now
    device_added = received_messages.get("/device/exists")
    if device_added:
        print("Successfully added device to track")
        return True
    else:
        print("Failed to add device to track")
        return False


@pytest.mark.usefixtures("osc_listener")
def test_transport_control(client):
    """Test basic transport controls"""
    # Clear any previous messages
    received_messages.clear()

    # Initial refresh to get current state
    client.send("/refresh", 1)
    time.sleep(0.5)  # Give Bitwig time to respond

    # Test play/stop
    initial_play_state = received_messages.get("/play", False)

    # Toggle play state
    client.send("/play", 1 if not initial_play_state else 0)
    time.sleep(0.5)

    # Verify play state changed
    new_play_state = wait_for_response("/play")

    # Return to original state
    client.send("/play", 1 if not new_play_state else 0)

    # Success if we got a response and the state changed
    assert new_play_state is not None, "Did not receive play state update from Bitwig"
    assert new_play_state != initial_play_state, "Play state did not change"


@pytest.mark.usefixtures("osc_listener")
def test_tempo_change(client):
    """Test changing the tempo"""
    # Clear any previous messages
    received_messages.clear()

    # Get current tempo
    client.send("/refresh", 1)
    time.sleep(0.5)

    initial_tempo = received_messages.get("/tempo/raw")
    assert initial_tempo is not None, "Couldn't get initial tempo"

    # Change tempo by +5 BPM, ensuring it's within the valid range (0-666)
    new_tempo = min(initial_tempo + 5, 666)
    client.send("/tempo/raw", new_tempo)
    time.sleep(0.5)

    # Verify tempo changed
    updated_tempo = wait_for_response("/tempo/raw")

    # Restore original tempo
    client.send("/tempo/raw", initial_tempo)

    # Success if we got a response and the tempo changed
    assert updated_tempo is not None, "Did not receive tempo update from Bitwig"
    assert abs(updated_tempo - new_tempo) < 0.1, "Tempo did not change to expected value"


@pytest.mark.usefixtures("osc_listener")
def test_track_volume(client):
    """Test changing a track's volume"""
    # Clear any previous messages
    received_messages.clear()

    # First track volume
    track_volume_addr = "/track/1/volume"

    # Get current volume
    client.send("/refresh", 1)
    time.sleep(0.5)

    initial_volume = received_messages.get(track_volume_addr)
    assert initial_volume is not None, "Couldn't get initial track volume"

    # Change volume to a value within the valid range (0-128)
    MAX_VALUE = 128
    test_volume = min(90, MAX_VALUE)
    client.send(track_volume_addr, test_volume)
    time.sleep(0.5)

    # Verify volume changed
    updated_volume = wait_for_response(track_volume_addr)

    # Restore original volume
    client.send(track_volume_addr, initial_volume)

    # Success if we got a response and the volume changed
    assert updated_volume is not None, "Did not receive volume update from Bitwig"
    assert abs(updated_volume - test_volume) < 0.1, "Volume did not change to expected value"


@pytest.mark.usefixtures("osc_listener")
def test_track_mute(client):
    """Test muting/unmuting a track"""
    # Clear any previous messages
    received_messages.clear()

    # First track mute
    track_mute_addr = "/track/1/mute"

    # Get current mute state
    client.send("/refresh", 1)
    time.sleep(0.5)

    initial_mute = received_messages.get(track_mute_addr, False)

    # Toggle mute state (only using 0 or 1 as values)
    client.send(track_mute_addr, 0 if initial_mute else 1)
    time.sleep(0.5)

    # Verify mute state changed
    new_mute_state = wait_for_response(track_mute_addr)

    # Return to original state
    client.send(track_mute_addr, 1 if initial_mute else 0)

    # Success if we got a response and the state changed
    assert new_mute_state is not None, "Did not receive mute state update from Bitwig"
    assert new_mute_state != initial_mute, "Mute state did not change"


@pytest.mark.usefixtures("osc_listener")
def test_device_parameter(client, ensure_device):
    """Test changing a device parameter"""
    # Skip if no device could be ensured
    if not ensure_device:
        pytest.skip("Could not ensure a device is available")

    # Clear any previous messages
    received_messages.clear()

    # Get device info first
    client.send("/refresh", 1)
    time.sleep(1.5)

    # Check if we have a device
    device_exists = received_messages.get("/device/exists")
    if not device_exists:
        pytest.skip("No device is currently selected/available in Bitwig")

    # Use a fixed parameter for simplicity (first parameter)
    param_index = 1
    param_addr = f"/device/param/{param_index}/value"
    param_exists_addr = f"/device/param/{param_index}/exists"

    # Check if parameter exists
    param_exists = received_messages.get(param_exists_addr)
    if not param_exists:
        pytest.skip(f"Parameter {param_index} does not exist or is not accessible")

    # Get current parameter value
    initial_value = received_messages.get(param_addr)
    assert initial_value is not None, f"Could not get value for parameter {param_index}"

    # Maximum value according to OSC protocol is typically 128
    MAX_VALUE = 128

    # Calculate a target value that's different from the current value but within range
    test_value = 20 if initial_value > 60 else 100
    test_value = min(test_value, MAX_VALUE)  # Ensure we don't exceed MAX_VALUE

    # Try to change the parameter
    client.send(param_addr, test_value)
    time.sleep(1)  # Give time for response

    # Check if value updated
    updated_value = wait_for_response(param_addr)

    # Restore original value
    client.send(param_addr, initial_value)

    # Success if we got a response and the value changed
    assert updated_value is not None, "Did not receive parameter update from Bitwig"
    assert (
        abs(updated_value - test_value) < 5
    ), f"Parameter value did not change as expected. Target: {test_value}, Actual: {updated_value}"
