"""
Bitwig OSC Integration Tests

This script tests communication with Bitwig Studio via OSC using the git-moss extension.
"""

import time

import pytest

from bitwig_mcp_server.osc.controller import BitwigOSCController
from tests.conftest import skip_if_bitwig_not_running

# Skip tests if Bitwig is not running

pytestmark = skip_if_bitwig_not_running


@pytest.fixture(scope="module")
def controller():
    """Create Bitwig OSC controller"""
    with BitwigOSCController() as controller:
        # Allow time for initial connection
        time.sleep(1)
        yield controller


def test_transport_control(controller):
    """Test basic transport controls"""
    # Get current play state
    controller.client.refresh()
    time.sleep(0.5)
    initial_play_state = controller.server.get_message("/play")

    # Toggle play state
    controller.client.play(not initial_play_state)
    time.sleep(0.5)

    # Verify play state changed
    new_play_state = controller.server.wait_for_message("/play")

    # Return to original state
    controller.client.play(initial_play_state)

    # Verify state changed
    assert new_play_state is not None, "Did not receive play state update from Bitwig"
    assert new_play_state != initial_play_state, "Play state did not change"


def test_tempo_change(controller):
    """Test changing the tempo"""
    # Get current tempo
    controller.client.refresh()
    time.sleep(0.5)

    initial_tempo = controller.server.get_message("/tempo/raw")
    assert initial_tempo is not None, "Couldn't get initial tempo"

    # Change tempo by +5 BPM
    new_tempo = min(initial_tempo + 5, 666)
    controller.client.set_tempo(new_tempo)
    time.sleep(0.5)

    # Verify tempo changed
    updated_tempo = controller.server.wait_for_message("/tempo/raw")

    # Restore original tempo
    controller.client.set_tempo(initial_tempo)

    # Verify change
    assert updated_tempo is not None, "Did not receive tempo update from Bitwig"
    assert abs(updated_tempo - new_tempo) < 0.1, "Tempo did not change to expected value"


def test_track_volume(controller):
    """Test changing a track's volume"""
    track_volume_addr = "/track/1/volume"

    # Get current volume
    controller.client.refresh()
    time.sleep(0.5)

    initial_volume = controller.server.get_message(track_volume_addr)
    assert initial_volume is not None, "Couldn't get initial track volume"

    # Change volume
    test_volume = 90 if initial_volume < 90 else 40
    controller.client.set_track_volume(1, test_volume)
    time.sleep(0.5)

    # Verify volume changed
    updated_volume = controller.server.wait_for_message(track_volume_addr)

    # Restore original volume
    controller.client.set_track_volume(1, initial_volume)

    # Verify change
    assert updated_volume is not None, "Did not receive volume update from Bitwig"
    assert abs(updated_volume - test_volume) < 1, "Volume did not change to expected value"


def test_track_mute(controller):
    """Test muting/unmuting a track"""
    track_mute_addr = "/track/1/mute"

    # Get current mute state
    controller.client.refresh()
    time.sleep(0.5)

    initial_mute = controller.server.get_message(track_mute_addr)

    # Toggle mute state
    controller.client.set_track_mute(1, not initial_mute)
    time.sleep(0.5)

    # Verify mute state changed
    new_mute_state = controller.server.wait_for_message(track_mute_addr)

    # Return to original state
    controller.client.set_track_mute(1, initial_mute)

    # Verify change
    assert new_mute_state is not None, "Did not receive mute state update from Bitwig"
    assert new_mute_state != initial_mute, "Mute state did not change"


def test_get_track_info(controller):
    """Test getting track information"""
    # Refresh to get current state
    controller.client.refresh()
    time.sleep(0.5)

    # Get track info
    track_info = controller.get_track_info(1)

    # Verify we got some basic info
    assert "name" in track_info, "Track name missing from track info"
    assert "volume" in track_info, "Volume missing from track info"
    assert "pan" in track_info, "Pan missing from track info"


def test_device_parameter(controller):
    """Test changing a device parameter"""
    # Refresh to get current state
    controller.client.refresh()
    time.sleep(0.5)

    # Check if we have a device
    device_exists = controller.server.get_message("/device/exists")
    if not device_exists:
        pytest.skip("No device is currently selected/available in Bitwig")

    # Use the first parameter
    param_index = 1
    param_addr = f"/device/param/{param_index}/value"
    param_exists_addr = f"/device/param/{param_index}/exists"

    # Check if parameter exists
    param_exists = controller.server.get_message(param_exists_addr)
    if not param_exists:
        pytest.skip(f"Parameter {param_index} does not exist or is not accessible")

    # Get current parameter value
    initial_value = controller.server.get_message(param_addr)
    assert initial_value is not None, f"Could not get value for parameter {param_index}"

    # Calculate a target value that's different from the current value
    test_value = 20 if initial_value > 60 else 100

    # Change the parameter
    controller.client.set_device_parameter(param_index, test_value)
    time.sleep(0.5)

    # Verify value changed
    updated_value = controller.server.wait_for_message(param_addr)

    # Restore original value
    controller.client.set_device_parameter(param_index, initial_value)

    # Verify update occurred
    assert updated_value is not None, "Did not receive parameter update from Bitwig"
    assert abs(updated_value - test_value) < 5, "Parameter value did not change as expected"
