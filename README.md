# Bitwig MCP Server

[![Release](https://img.shields.io/github/v/release/jxstanford/bitwig-mcp-server)](https://img.shields.io/github/v/release/jxstanford/bitwig-mcp-server)
[![Build status](https://img.shields.io/github/actions/workflow/status/jxstanford/bitwig-mcp-server/main.yml?branch=main)](https://github.com/jxstanford/bitwig-mcp-server/actions/workflows/main.yml?query=branch%3Amain)
[![codecov](https://codecov.io/gh/jxstanford/bitwig-mcp-server/branch/main/graph/badge.svg)](https://codecov.io/gh/jxstanford/bitwig-mcp-server)
[![License](https://img.shields.io/github/license/jxstanford/bitwig-mcp-server)](https://img.shields.io/github/license/jxstanford/bitwig-mcp-server)

A Model Context Protocol (MCP) server for Bitwig Studio that allows Claude to control your DAW.

## Features

- **AI-Powered Music Production**: Control Bitwig Studio with Claude via MCP
- **Transport Controls**: Play, stop, and set tempo
- **Mixer Controls**: Adjust volume, pan, and mute/unmute tracks
- **Device Controls**: Manipulate device parameters
- **Project Information**: Access track and device information
- **Templates and Prompts**: Pre-configured workflows for common tasks

## Installation

### Prerequisites

- Python 3.10+
- [Bitwig Studio](https://www.bitwig.com/) 5.2+
- [Driven by Moss](https://www.mossgrabers.de/Software/Bitwig/Bitwig.html#5.2) 5.2+
- [Claude Desktop](https://claude.ai/download) app with MCP support

### Install from GitHub

```bash
# Clone the repository
git clone https://github.com/jxstanford/bitwig-mcp-server.git
cd bitwig-mcp-server

# Install dependencies
uv sync
```

## Usage

### 1. Configure Bitwig Studio

1. If necessary, add a virtual MIDI device for OSC
2. Follow Driven by Moss installation instructions for Bitwig 5.2+
3. Open or restart Bitwig Studio
4. Go to Settings > Controllers
5. Click "Add Controller" and select "Open Sound Control" and "OSC"
6. Configure the receive port (default: 8000) and send port (default: 9000)
7. Enable the controller

### 2. Run the Bitwig MCP Server

```bash
# Run the server with default settings
python -m bitwig_mcp_server

# Or run with custom settings
python -m bitwig_mcp_server --host 127.0.0.1 --send-port 8000 --receive-port 9000 --transport stdio --debug
```

### 3. Add to Claude Desktop

```bash
# Install the server in Claude Desktop
mcp install bitwig_mcp_server/__main__.py
```

Then open Claude Desktop and select the Bitwig MCP Server from the MCP Servers dropdown.

## Available Tools

The Bitwig MCP Server provides the following tools:

### Transport Controls

- **play**: Toggle play/pause state or set it to a specific state
- **stop**: Stop playback
- **set_tempo**: Set the tempo in beats per minute

### Track Controls

- **set_track_volume**: Set track volume (0-128)
- **set_track_pan**: Set track pan position (0-128)
- **set_track_mute**: Mute, unmute, or toggle mute state for a track

### Device Controls

- **set_device_parameter**: Set a device parameter value (0-128)

### Information

- **get_project_info**: Get information about the current Bitwig project
- **get_tracks_info**: Get information about all tracks in the project
- **get_track_info**: Get information about a specific track
- **get_device_parameters**: Get information about the selected device parameters

## Available Resources

- **bitwig://project/info**: Project information
- **bitwig://transport**: Transport state
- **bitwig://tracks**: All tracks in the project
- **bitwig://track/{index}**: Specific track information
- **bitwig://devices**: Active devices
- **bitwig://device/parameters**: Parameters for the selected device

## Example Prompts

- **setup_mixing_session**: Set up a new mixing session with default settings
- **create_track_template**: Create a track template with specific devices and settings
- **optimize_track_settings**: Get recommendations for optimizing track settings

## Configuration

The server can be configured through:

1. Environment variables or `.env` file
2. Command line arguments
3. Settings in `bitwig_mcp_server/settings.py`

### Command Line Arguments

```bash
python -m bitwig_mcp_server --help
```

## Development

### Environment Setup

```bash
# Install dev dependencies
uv sync

# Install pre-commit hooks
uv run pre-commit install
```

### Running Tests

```bash
# Run unit tests (no Bitwig required)
make test

# Run all tests including Bitwig integration tests
# (requires Bitwig Studio running with OSC enabled)
make test-all
```

### Code Quality

```bash
# Run code quality checks
make check
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
