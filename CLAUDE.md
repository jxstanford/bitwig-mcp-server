# Bitwig MCP Server - Claude Code Guide

## Project Overview

This project creates a server that allows Claude to control Bitwig Studio through the Model Context Protocol (MCP). It translates between MCP requests from Claude and OSC commands to Bitwig Studio's control API.

## External References

### MCP SDK and Documentation

- MCP python-sdk GitHub Repository: https://github.com/modelcontextprotocol/python-sdk
- MCP documentation: https://modelcontextprotocol.io/
- GitHub Repository: https://github.com/anthropics/anthropic-sdk-python
- Documentation: https://docs.anthropic.com/

### Project-specific references

- coding guidelines: https://github.com/jxstanford/prompts-and-context/code
- MCP development guidelines: https://github.com/jxstanford/prompts-and-context/mcp
- Bitwig and OSC documentation: https://github.com/jxstanford/prompts-and-context/bitwig-mcp-server

## Current Status

### Implemented Components

- OSC Communication Layer:
  - `BitwigOSCClient`: Sends OSC messages to Bitwig (`bitwig_mcp_server/osc/client.py`)
  - `BitwigOSCServer`: Receives OSC messages from Bitwig (`bitwig_mcp_server/osc/server.py`)
  - `BitwigOSCController`: Coordinates bidirectional communication (`bitwig_mcp_server/osc/controller.py`)
- MCP Server Framework:
  - `BitwigMCPServer`: Main server class integrating MCP and OSC (moved to `bitwig_mcp_server/mcp/server.py`)
  - `app.py`: High-level application coordinator (`bitwig_mcp_server/app.py`)
  - MCP Tools: Basic Bitwig control operations (`bitwig_mcp_server/mcp/tools.py`)
  - MCP Resources: Queryable Bitwig state information (`bitwig_mcp_server/mcp/resources.py`)
  - MCP Prompts: Templates for common workflows (`bitwig_mcp_server/mcp/prompts.py`)

### Development Workflow

When working on this codebase:

1. Use `pytest` for running tests: `pytest tests/`
2. For type checking: `mypy bitwig_mcp_server/`
3. For linting: `ruff check bitwig_mcp_server/`
4. For code formatting: `black bitwig_mcp_server/`

## Project Structure

### Core Components

- `bitwig_mcp_server/app.py`: Main application coordinator (high-level)
- `bitwig_mcp_server/settings.py`: Configuration settings
- `bitwig_mcp_server/mcp/`: Model Context Protocol implementation
  - `bitwig_mcp_server/mcp/server.py`: MCP server implementation
  - `bitwig_mcp_server/mcp/tools.py`: Tools Claude can use to control Bitwig
  - `bitwig_mcp_server/mcp/resources.py`: Resources Claude can query about Bitwig's state
  - `bitwig_mcp_server/mcp/prompts.py`: Templates for common music production workflows
- `bitwig_mcp_server/osc/`: Open Sound Control implementation
  - `bitwig_mcp_server/osc/client.py`: Client to send OSC messages to Bitwig
  - `bitwig_mcp_server/osc/server.py`: Server to receive OSC messages from Bitwig
  - `bitwig_mcp_server/osc/controller.py`: Coordinates OSC client and server
  - `bitwig_mcp_server/osc/error_handler.py`: Handles OSC communication errors
  - `bitwig_mcp_server/osc/exceptions.py`: Custom exceptions for OSC communication

### Testing Structure

- `tests/mcp/`: Unit tests for MCP components
  - `tests/mcp/test_server.py`: Tests for the MCP server
  - `tests/mcp/test_tools.py`: Tests for MCP tools
  - `tests/mcp/test_resources.py`: Tests for MCP resources
- `tests/osc/`: Unit tests for OSC components
- `tests/integration/`: Integration tests
  - `tests/integration/test_mcp_integration.py`: Tests for MCP server integration
  - `tests/integration/test_osc_integration.py`: Tests for OSC communication

## Implementation Guidelines

### MCP Tools Design

- Tools should follow the MCP Tool schema pattern
- Each tool should map to one or more OSC commands
- Error handling should be comprehensive and informative
- Consider user experience when designing tool APIs

### MCP Resources Design

- Resources should provide clear, structured information
- Use URIs that follow a consistent pattern
- Cache resource data appropriately to avoid excessive OSC traffic
- Consider versioning for evolving resources

## TODO Items

### Resource Improvements

- [ ] Add device-specific URIs with indices: `bitwig://device/{index}` and `bitwig://device/{index}/parameters`
- [x] Add device siblings and layers resources (`bitwig://device/siblings` and `bitwig://device/layers`)
- [ ] Handle URL encoding in resource URIs (currently `{index}` is encoded as `%7Bindex%7D`)
- [x] Add comprehensive tests for the new device resources
- [x] Fix OSC integration tests to properly select devices on tracks

### Integration Improvements

- [ ] Fix app integration tests that use the MCP protocol
- [ ] Ensure MCP server tests work with mock controllers

### Development Tasks

1. Expand the existing tools in `tools.py` to cover more Bitwig functionality
2. Add more detailed resource representations in `resources.py`
3. Create additional prompt templates in `prompts.py` for common workflows
4. Ensure robust error handling throughout the codebase
5. Add comprehensive tests for all new functionality

## Testing

For testing:

- Unit tests are in the `tests/` directory
- Integration tests that check OSC functionality are in `tests/integration/`
- Ensure venv is active
- Run tests with `pytest tests/` or `make test`
