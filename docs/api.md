# Bitwig MCP Server API Documentation

This document provides comprehensive documentation for the Bitwig MCP Server API, which enables control of Bitwig Studio through the Model Context Protocol (MCP).

## Overview

The Bitwig MCP Server exposes functionality through two main interfaces:

1. **MCP Tools**: Actions that Claude can invoke to control Bitwig Studio
2. **MCP Resources**: Data from Bitwig Studio that Claude can access

The server communicates with Bitwig Studio via OSC (Open Sound Control) protocol, translating MCP requests into OSC messages and vice versa.

## MCP Tools Reference

### Transport Controls

#### `play`

Toggle playback state in Bitwig Studio.

**Parameters:**

- `state` (optional bool): True to play, False to stop, None to toggle (default)

**Returns:**

- String status message

**Example:**

```python
await client.call_tool("play", {"state": True})  # Start playback
await client.call_tool("play", {"state": False})  # Stop playback
await client.call_tool("play")  # Toggle playback
```

#### `stop`

Stop playback in Bitwig Studio.

**Parameters:**

- None

**Returns:**

- String status message

**Example:**

```python
await client.call_tool("stop")
```

#### `set_tempo`

Set the project tempo.

**Parameters:**

- `bpm` (float): Tempo in beats per minute (20-999)

**Returns:**

- String status message

**Example:**

```python
await client.call_tool("set_tempo", {"bpm": 120.5})
```

#### `toggle_record`

Toggle record state in Bitwig Studio.

**Parameters:**

- None

**Returns:**

- String status message

**Example:**

```python
await client.call_tool("toggle_record")
```

### Track Controls

#### `set_track_volume`

Set the volume level of a track.

**Parameters:**

- `track_index` (int): Track index (1-based)
- `volume` (float): Volume value (0-128, where 64 is 0dB)

**Returns:**

- String status message

**Example:**

```python
await client.call_tool("set_track_volume", {"track_index": 1, "volume": 80})
```

#### `set_track_pan`

Set the pan position of a track.

**Parameters:**

- `track_index` (int): Track index (1-based)
- `pan` (float): Pan value (0-128, where 64 is center)

**Returns:**

- String status message

**Example:**

```python
await client.call_tool("set_track_pan", {"track_index": 1, "pan": 40})  # Pan left
```

#### `set_track_mute`

Mute or unmute a track.

**Parameters:**

- `track_index` (int): Track index (1-based)
- `mute` (bool): True to mute, False to unmute

**Returns:**

- String status message

**Example:**

```python
await client.call_tool("set_track_mute", {"track_index": 1, "mute": True})
```

#### `toggle_track_mute`

Toggle mute state of a track.

**Parameters:**

- `track_index` (int): Track index (1-based)

**Returns:**

- String status message

**Example:**

```python
await client.call_tool("toggle_track_mute", {"track_index": 1})
```

#### `toggle_track_solo`

Toggle solo state of a track.

**Parameters:**

- `track_index` (int): Track index (1-based)

**Returns:**

- String status message

**Example:**

```python
await client.call_tool("toggle_track_solo", {"track_index": 1})
```

#### `toggle_track_arm`

Toggle record arm state of a track.

**Parameters:**

- `track_index` (int): Track index (1-based)

**Returns:**

- String status message

**Example:**

```python
await client.call_tool("toggle_track_arm", {"track_index": 1})
```

### Device Controls

#### `set_device_parameter`

Set a device parameter value.

**Parameters:**

- `param_index` (int): Parameter index (1-based)
- `value` (float): Parameter value (0-128)

**Returns:**

- String status message

**Example:**

```python
await client.call_tool("set_device_parameter", {"param_index": 1, "value": 100})
```

## MCP Resources Reference

### `bitwig://project/info`

Get information about the current Bitwig project.

**Returns:**

- Text with project name, tempo, and time signature

**Example:**

```python
result = await client.read_resource("bitwig://project/info")
```

### `bitwig://transport`

Get current transport state.

**Returns:**

- Text with play state, record state, tempo, and position

**Example:**

```python
result = await client.read_resource("bitwig://transport")
```

### `bitwig://tracks`

Get information about all tracks in the project.

**Returns:**

- Text with track names, volumes, pan positions, and mute/solo states

**Example:**

```python
result = await client.read_resource("bitwig://tracks")
```

### `bitwig://track/{index}`

Get detailed information about a specific track.

**Parameters:**

- `index` (int): Track index (1-based)

**Returns:**

- Text with detailed track information

**Example:**

```python
result = await client.read_resource("bitwig://track/1")
```

### `bitwig://devices`

Get information about active devices.

**Returns:**

- Text with device names and chain information

**Example:**

```python
result = await client.read_resource("bitwig://devices")
```

### `bitwig://device/parameters`

Get parameters for the selected device.

**Returns:**

- Text with parameter names and values

**Example:**

```python
result = await client.read_resource("bitwig://device/parameters")
```

## Error Handling

The server provides detailed error messages for various error conditions:

- **Parameter Validation Errors**: When parameters don't meet constraints
- **OSC Communication Errors**: When there's an issue communicating with Bitwig
- **Resource Not Found Errors**: When requested resources don't exist

Example error responses:

```json
{
  "error": "Value error",
  "message": "Tempo 1000 outside valid range (20-999)"
}
```

```json
{
  "error": "Resource error",
  "message": "Track 10 not found"
}
```

## Client Usage Examples

### Python MCP Client Example

```python
import asyncio
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.types import AnyUrl

async def control_bitwig():
    # Connect to the Bitwig MCP server
    async with stdio_client(
        StdioServerParameters(command="python", args=["-m", "bitwig_mcp_server"])
    ) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Start playback
            result = await session.call_tool("play", {"state": True})
            print(f"Play result: {result}")

            # Get project info
            result = await session.read_resource(AnyUrl("bitwig://project/info"))
            print(f"Project info: {result}")

            # Set tempo to 120 BPM
            result = await session.call_tool("set_tempo", {"bpm": 120})
            print(f"Set tempo result: {result}")

            # Wait for 3 seconds
            await asyncio.sleep(3)

            # Stop playback
            result = await session.call_tool("stop")
            print(f"Stop result: {result}")

asyncio.run(control_bitwig())
```

### Using the Bitwig MCP Client Library

```python
import asyncio
from bitwig_mcp_server.mcp.client import BitwigMCPClient

async def main():
    async with BitwigMCPClient() as client:
        # Get project info
        project_info = await client.get_project_info()
        print(f"Project info:\n{project_info}")

        # Set tempo to 110 BPM
        result = await client.set_tempo(110)
        print(f"Result: {result}")

        # Start playback
        result = await client.play()
        print(f"Result: {result}")

        # Wait for 3 seconds
        await asyncio.sleep(3)

        # Stop playback
        result = await client.stop()
        print(f"Result: {result}")

asyncio.run(main())
```

## Configuration

The Bitwig MCP Server can be configured via:

1. **Environment Variables**:

   - `BITWIG_HOST`: Bitwig host IP address (default: "127.0.0.1")
   - `BITWIG_SEND_PORT`: Port to send OSC messages to Bitwig (default: 8000)
   - `BITWIG_RECEIVE_PORT`: Port to receive OSC messages from Bitwig (default: 9000)
   - `MCP_PORT`: Port for MCP server HTTP/SSE transport (default: 8080)
   - `LOG_LEVEL`: Logging level (default: "INFO")

2. **Command Line Arguments**:

   - `--host`: Bitwig host IP address
   - `--send-port`: Port to send OSC messages to Bitwig
   - `--receive-port`: Port to receive OSC messages from Bitwig
   - `--transport`: Transport protocol to use ("stdio" or "sse")
   - `--log-level`: Logging level
   - `--mcp-port`: Port for MCP server HTTP/SSE transport

3. **Settings File**:
   - `.env` file in the project root

## Limitations and Known Issues

1. **OSC Protocol Limitations**:

   - Bitwig's OSC implementation does not support creating new tracks or devices
   - Some parameters might not be fully accessible via OSC

2. **State Management**:

   - The server does not maintain state between sessions
   - Each new session will need to query Bitwig for current state

3. **Error Recovery**:
   - If Bitwig becomes unresponsive, the server may need to be restarted

## Troubleshooting

### Common Issues

1. **Connection Failures**:

   - Ensure Bitwig Studio is running
   - Verify OSC is enabled in Bitwig (Settings > Controllers > Generic OSC)
   - Check port configurations match between Bitwig and the server

2. **Missing Resources**:

   - Some resources require selecting a track or device in Bitwig
   - Verify track indices are correct (1-based indexing)

3. **Parameter Range Errors**:
   - Check that parameters are within valid ranges
   - Volume and pan are typically 0-128
   - Tempo must be 20-999 BPM
