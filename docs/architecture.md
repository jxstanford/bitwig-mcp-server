# Bitwig MCP Server Architecture

This document outlines the architecture of the Bitwig MCP Server, explaining how it bridges Claude's Model Context Protocol (MCP) with Bitwig Studio's OSC API.

## Overview

The Bitwig MCP Server acts as a translation layer between:

1. **Claude Desktop** using the Model Context Protocol (MCP)
2. **Bitwig Studio** using Open Sound Control (OSC)

```
┌───────────────┐      ┌───────────────────────┐      ┌───────────────┐
│               │      │                       │      │               │
│     Claude    │◄────►│  Bitwig MCP Server    │◄────►│    Bitwig     │
│    Desktop    │ MCP  │                       │ OSC  │    Studio     │
│               │      │                       │      │               │
└───────────────┘      └───────────────────────┘      └───────────────┘
```

## Architecture Components

### Core Components

The server architecture consists of the following core components:

1. **BitwigFastMCP** - Main FastMCP server implementation

   - Registers tools, resources, and prompts
   - Manages server lifecycle
   - Handles translation between MCP and OSC

2. **OSC Communication Layer**

   - **BitwigOSCClient** - Sends OSC messages to Bitwig
   - **BitwigOSCServer** - Receives OSC messages from Bitwig
   - **BitwigOSCController** - Coordinates bidirectional communication

3. **MCP Integration**
   - **Resource Management** - Exposes Bitwig resources via MCP
   - **Tool Integration** - Provides Bitwig control tools for Claude
   - **Prompt Templates** - Offers pre-configured workflows for common tasks

### Architectural Patterns

The server follows these architectural patterns:

1. **Hexagonal Architecture (Ports and Adapters)**

   - Core domain (Bitwig control model)
   - Input ports (MCP server interface)
   - Output ports (OSC client interface)
   - Adapters (FastMCP and OSC implementations)

2. **Dependency Injection**
   - Components can be tested in isolation
   - OSC controller is injected into the FastMCP server
   - Loose coupling between modules

## Translation Layer

The server translates between these two protocols:

### MCP to OSC Translation

When Claude calls an MCP tool:

1. The tool handler is invoked with parameters
2. Parameters are validated
3. The handler calls appropriate OSC client methods
4. OSC messages are sent to Bitwig
5. Results are formatted as MCP responses

### OSC to MCP Translation

When reading Bitwig state:

1. OSC client sends query messages
2. OSC server receives response messages
3. Messages are parsed and state is extracted
4. State is formatted as MCP resource content
5. Claude receives the formatted resource

## Dependencies

The server depends on the following libraries:

1. **MCP Python SDK** (`mcp` package)

   - FastMCP server implementation
   - Client and server session handling
   - Tool, resource, and prompt models

2. **python-osc**

   - OSC message formatting and parsing
   - UDP transport for OSC messages

3. **Pydantic**
   - Data validation and settings management
   - Type checking and conversion

## Flow Diagrams

### Tool Execution Flow

```
┌───────────┐    ┌─────────────┐    ┌───────────────┐    ┌──────────────┐    ┌─────────┐
│           │    │             │    │               │    │              │    │         │
│  Claude   │───►│  FastMCP    │───►│  OSC Client   │───►│  OSC Message │───►│ Bitwig  │
│           │    │  Tool       │    │  Method       │    │              │    │         │
│           │    │             │    │               │    │              │    │         │
└───────────┘    └─────────────┘    └───────────────┘    └──────────────┘    └─────────┘
       ▲                                                                          │
       │                                                                          │
       │               ┌─────────────┐    ┌───────────────┐                      │
       │               │             │    │               │                      │
       └───────────────┤  Response   │◄───┤  OSC Server   │◄─────────────────────┘
                       │  Formatter  │    │  Listener     │
                       │             │    │               │
                       └─────────────┘    └───────────────┘
```

### Resource Access Flow

```
┌───────────┐    ┌─────────────┐    ┌───────────────┐    ┌──────────────┐    ┌─────────┐
│           │    │             │    │               │    │              │    │         │
│  Claude   │───►│  FastMCP    │───►│  OSC Client   │───►│  OSC Message │───►│ Bitwig  │
│           │    │  Resource   │    │  Query        │    │              │    │         │
│           │    │             │    │               │    │              │    │         │
└───────────┘    └─────────────┘    └───────────────┘    └──────────────┘    └─────────┘
       ▲                                                                          │
       │                                                                          │
       │               ┌─────────────┐    ┌───────────────┐                      │
       │               │             │    │               │                      │
       └───────────────┤  Resource   │◄───┤  OSC Server   │◄─────────────────────┘
                       │  Formatter  │    │  Response     │
                       │             │    │               │
                       └─────────────┘    └───────────────┘
```

## Error Handling

The server implements the following error handling strategies:

1. **Parameter Validation**

   - Type checking and range validation for all parameters
   - Detailed error messages for invalid inputs

2. **OSC Communication Errors**

   - Timeouts for message sending and receiving
   - Error reporting for connection issues

3. **Bitwig State Validation**
   - Checking for object existence before operations
   - Graceful degradation for missing features

## Security Considerations

1. **Network Security**

   - Local host-only connections by default
   - No external access to OSC ports

2. **Input Validation**
   - All parameters are validated before use
   - Protection against invalid inputs

## Future Extensions

The architecture is designed to be extensible for future features:

1. **Additional Bitwig Features**

   - Track creation and management
   - Arrangement and editing
   - Plugin parameter control

2. **Enhanced Workflows**

   - Audio analysis and recommendations
   - Project management tools
   - Music composition assistance

3. **User Interface**
   - Web-based control panel
   - Status monitoring dashboard
   - Configuration management
