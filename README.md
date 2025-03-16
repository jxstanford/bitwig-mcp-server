# Bitwig MCP Server

A Python library for robust integration with Bitwig Studio's OSC API, providing parameter validation, response parsing, and high-level workflow tools for music production.

## Features

- **Robust OSC Communication**: Reliable message sending and receiving with proper error handling
- **Comprehensive Parameter Validation**: Type checking and range validation for all API parameters
- **Intelligent Response Parsing**: Parse various OSC message formats and handle error conditions
- **High-Level Workflow Tools**: Specialized tools for common music production workflows
- **Fully Unit Tested**: Comprehensive test suite ensuring reliability

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/bitwig-osc-integration.git
cd bitwig-osc-integration

# Install dependencies
pip install -r requirements.txt
```

## Requirements

- Python 3.8+
- python-osc
- Bitwig Studio 5.0+ with OSC enabled

## Configuring Bitwig Studio

1. Open Bitwig Studio
2. Go to Settings > Controllers
3. Add a new Generic OSC controller
4. Configure the ports to match those used in your code (default: send 8000, receive 9000)

## Basic Usage

```python
from bitwig_workflows import BitwigWorkflows

# Create a new workflows client with default connection parameters
with BitwigWorkflows() as bitwig:
    # Basic transport controls
    bitwig.client.play()
    bitwig.client.set_tempo(120)

    # Get information about tracks
    tracks = bitwig.mixer.get_all_tracks()
    for track in tracks:
        print(f"Track {track.index}: {track.name} - Volume: {track.volume}")

    # Set up a recording session
    bitwig.setup_recording_session(track_index=0)
```

## Architecture

The library is organized into several key components:

### Parameter Validation (`parameter_validation.py`)

Handles validation of all API parameters, ensuring correct types and ranges.

```python
from parameter_validation import ParameterValidator

# Validate a track index
track_index = ParameterValidator.validate_int(user_input, min_val=0,
                                             param_name="Track index")

# Validate a volume level
volume = ParameterValidator.validate_float(user_input, min_val=0.0, max_val=1.0,
                                          param_name="Volume")
```

### OSC Response Parser (`osc_response_parser.py`)

Handles parsing of OSC messages and responses from Bitwig Studio.

```python
from osc_response_parser import OscResponse, ResponseParser

# Parse an OSC message into a response object
response = ResponseParser.parse_message(message)

# Check for errors and extract values
if response.is_error:
    print(f"Error: {response.error_message}")
else:
    value = response.get_float(0)
```

### OSC Client (`osc_client.py`)

Provides low-level and high-level clients for OSC communication with Bitwig.

```python
from osc_client import BitwigApiClient

# Create a client
client = BitwigApiClient()
client.start()

# Control transport
client.play()
client.set_tempo(128.5)

# Control tracks
client.set_track_volume(0, 0.8)
client.set_track_pan(1, -0.3)

client.stop()
```

### Workflows (`bitwig_workflows.py`)

Provides high-level workflow tools for common music production tasks.

```python
from bitwig_workflows import BitwigWorkflows

with BitwigWorkflows() as bitwig:
    # Set up a mixing session
    bitwig.setup_mixing_session()

    # Automate a filter sweep
    bitwig.automate_filter_sweep(track_index=2, device_index=1,
                                param_index=0, duration_sec=8.0)
```

## API Documentation

### Transport Controls

```python
# Play, stop, record
client.play()
client.stop()
client.record()

# Set tempo
client.set_tempo(120.5)

# Position control
transport.play_from_start()
transport.set_loop_range(4.0, 12.0)
transport.toggle_loop()
```

### Track Controls

```python
# Get track information
track_count = client.get_track_count()
track_name = client.get_track_name(track_index)

# Set track parameters
client.set_track_volume(track_index, volume)  # 0.0 to 1.0
client.set_track_pan(track_index, pan)  # -1.0 to 1.0

# Using the mixer control
track_info = mixer.get_track_info(track_index)
all_tracks = mixer.get_all_tracks()
mixer.reset_mixer()
mixer.set_track_levels({0: 0.8, 1: 0.7, 2: 0.75})
```

### Device Controls

```python
# Get device parameters
parameters = devices.get_device_parameters(track_index, device_index)

# Set device parameters
devices.set_device_parameter(track_index, device_index, param_index, value)
devices.toggle_device_enabled(track_index, device_index)

# Automation
workflows.automate_filter_sweep(track_index, device_index, param_index, duration_sec)
```

## Error Handling

The library provides comprehensive error handling:

```python
from osc_client import OscClientError
from parameter_validation import ValidationError

try:
    client.set_track_volume(track_index, volume)
except ValidationError as e:
    print(f"Invalid parameter: {e}")
except OscClientError as e:
    print(f"Communication error: {e}")
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- The Bitwig team for providing the OSC API
- The python-osc library developers
