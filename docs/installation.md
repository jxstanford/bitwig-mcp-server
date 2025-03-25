# Bitwig MCP Server Installation Guide

This guide provides step-by-step instructions for installing and configuring the Bitwig MCP Server, which allows controlling Bitwig Studio through the Model Context Protocol (MCP).

## Prerequisites

Before installing the Bitwig MCP Server, ensure you have the following:

- Python 3.10+
- [Bitwig Studio](https://www.bitwig.com/) 5.2+
- [Driven by Moss](https://www.mossgrabers.de/Software/Bitwig/Bitwig.html#5.2) 5.2+
- [Claude Desktop](https://claude.ai/download) app with MCP support

## Installation Methods

### Option 1: Using `pip`

The simplest way to install the Bitwig MCP Server is via pip:

```bash
pip install bitwig-mcp-server
```

### Option 2: From Source

To install from source:

1. Clone the repository:

   ```bash
   git clone https://github.com/jxstanford/bitwig-mcp-server.git
   cd bitwig-mcp-server
   ```

2. Install the package with pip:

   ```bash
   pip install -e .
   ```

   Or use uv:

   ```bash
   uv sync
   ```

## Configuring Bitwig Studio

Before you can use the Bitwig MCP Server, you need to configure Bitwig Studio to support OSC communication:

1. Open Bitwig Studio
2. Go to **Settings > Controllers**
3. Click the **+ button** to add a new controller
4. Select **Generic > Open Sound Control**
5. Configure the OSC settings:

   - **Remote Host**: "127.0.0.1" (or the IP address of the machine running the server)
   - **Remote Send Port**: 9000 (this is the port the server listens on)
   - **Remote Listen Port**: 8000 (this is the port the server sends to)
   - **Use SLIP**: Unchecked

6. Click "Apply" to save the settings

## Running the Server

### Command Line Usage

You can run the Bitwig MCP Server from the command line:

```bash
# Run with default settings
python -m bitwig_mcp_server

# Run with custom settings
python -m bitwig_mcp_server --host 127.0.0.1 --send-port 8000 --receive-port 9000 --transport stdio --log-level debug
```

### Command Line Options

The server supports the following command line options:

- `--host`: Bitwig host IP address (default: "127.0.0.1")
- `--send-port`: Port to send OSC messages to Bitwig (default: 8000)
- `--receive-port`: Port to receive OSC messages from Bitwig (default: 9000)
- `--transport`: Transport protocol to use ("stdio" or "sse", default: "stdio")
- `--log-level`: Logging level (default: "info")
- `--mcp-port`: Port for MCP server HTTP/SSE transport (default: 8080)

## Integrating with Claude

To use the Bitwig MCP Server with Claude, you need to set up a new MCP server in Claude Desktop:

1. Open Claude Desktop
2. Go to **Settings > MCP Servers**
3. Click **Add New Server**
4. Enter the following details:
   - **Server Name**: "Bitwig Studio"
   - **Command**: "python" (or path to your Python executable)
   - **Arguments**: "-m bitwig_mcp_server"
5. Click **Save**

Alternatively, you can use the `mcp` CLI tool to install the server:

```bash
pip install mcp[cli]
mcp install "python -m bitwig_mcp_server" --name "Bitwig Studio"
```

## Verifying Installation

To verify that the Bitwig MCP Server is working correctly:

1. Run the server:

   ```bash
   python -m bitwig_mcp_server
   ```

2. Run the example client to test basic functionality:

   ```bash
   python -m examples.client_examples
   ```

3. If everything is working correctly, you should see the client connecting to the server and controlling Bitwig Studio

## Troubleshooting

### Common Issues

#### Connection Failures

If the server fails to connect to Bitwig Studio:

- Ensure Bitwig Studio is running
- Verify that the OSC controller is correctly configured in Bitwig
- Check that the ports match between Bitwig and the server
- Make sure no firewall is blocking the communication

#### OSC Not Working

If OSC communication is not working:

- Restart Bitwig Studio after configuring the OSC controller
- Ensure no other applications are using the same ports
- Try using different ports and update both Bitwig and server configurations

#### Server Crashes

If the server crashes:

- Check the logs for errors
- Ensure you're using a compatible Python version
- Verify that all dependencies are properly installed

## Environment Variables

The Bitwig MCP Server can also be configured using environment variables:

- `BITWIG_HOST`: Bitwig host IP address
- `BITWIG_SEND_PORT`: Port to send OSC messages to Bitwig
- `BITWIG_RECEIVE_PORT`: Port to receive OSC messages from Bitwig
- `LOG_LEVEL`: Logging level
- `MCP_PORT`: Port for MCP server HTTP/SSE transport

These can be set in your shell or in a `.env` file in the project directory.

## Docker Installation

You can also run the Bitwig MCP Server in a Docker container:

```bash
# Build the Docker image
docker build -t bitwig-mcp-server .

# Run the container
docker run -p 8000:8000 -p 9000:9000 -p 8080:8080 bitwig-mcp-server
```

Note that when using Docker, you'll need to configure the networking appropriately to allow communication between the container and Bitwig Studio.

## Next Steps

After installing the Bitwig MCP Server, you can:

- Read the [API Documentation](API.md) to learn about available tools and resources
- Try the [example scripts](../examples/) to see how to use the client library
- Configure Claude to use the Bitwig MCP Server for music production tasks
