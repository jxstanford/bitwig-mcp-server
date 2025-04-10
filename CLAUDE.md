# Bitwig MCP Server - Claude Code Guide

## Project Overview

This project creates a server that allows Claude to control Bitwig Studio through the Model Context Protocol (MCP). It translates between MCP requests from Claude and OSC commands to Bitwig Studio's control API.

## Project-Specific Guidelines

### Development Workflow

For this project, follow these specific steps:

1. Use an incremental approach focusing on one feature at a time
2. Update/create appropriate tests for each change
3. Follow this test procedure for each change:
   - Run `pytest tests/` to verify changes
   - Run `mypy bitwig_mcp_server/` for type checking
   - Run `ruff check bitwig_mcp_server/` for linting
   - Run `black bitwig_mcp_server/` for code formatting

### MCP Implementation Guidelines

- Tools should follow the MCP Tool schema pattern
- Each tool should map to one or more OSC commands
- Error handling should be comprehensive and informative
- Consider user experience when designing tool APIs
- Resources should provide clear, structured information
- Use URIs that follow a consistent pattern
- Cache resource data appropriately to avoid excessive OSC traffic

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
- Bitwig OSC Reference: https://github.com/git-moss/DrivenByMoss-Documentation/blob/master/Generic-Tools-Protocols/Open-Sound-Control-(OSC).md

### Music Production Resources

Our prioritization of features is informed by standard music production workflows. For additional resources on music production workflows, consider the following common references:

- Bitwig Studio Manual: Official documentation covering Bitwig's workflow and features
- Ableton's "Making Music - 74 Creative Strategies": Excellent resource on music creation workflows
- Rick Snoman's "Dance Music Manual": Contains detailed production workflows
- "Mixing Secrets for the Small Studio" by Mike Senior: Covers workflow for the mixing phase
- "The Art of Music Production" by Richard James Burgess: Historical and practical music production processes

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
  - `tests/integration/test_app_integration.py`: Tests for the application using MCP client
  - `tests/integration/test_mcp_integration.py`: Tests for MCP server integration with Bitwig
  - `tests/integration/test_osc_integration.py`: Tests for OSC communication
  - `tests/integration/test_browser_pagination_integration.py`: Tests for browser pagination

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

## User Story Implementation Roadmap

Our implementation is guided by the user stories documented in `docs/user_stories.md`. Below is our roadmap that maps the user stories to specific implementation tasks.

### Currently Implemented

- ✅ Basic transport control (play/stop)
- ✅ Tempo adjustment
- ✅ Basic track parameter manipulation (volume, pan, mute)
- ✅ Basic device parameter control
- ✅ Error handling with meaningful messages
- ✅ Type validation for parameters
- ✅ Device navigation (siblings, layers)
- ✅ Browser navigation via OSC
- ✅ Browser state resources and tools
- ✅ Browser search infrastructure with ChromaDB
- ✅ Device recommendation system foundation
- ✅ Comprehensive MCP integration tests with Bitwig Studio
- ✅ Improved app integration tests for the MCP server
- ✅ Browser pagination with multi-page device navigation

### In Progress

#### Resource Improvements

- [x] Add device-specific URIs with indices: `bitwig://device/{index}` and `bitwig://device/{index}/parameters`
- [x] Add device siblings and layers resources (`bitwig://device/siblings` and `bitwig://device/layers`)
- [x] Handle URL encoding in resource URIs (using proper URI parsing)
- [x] Add comprehensive tests for the new device resources
- [x] Fix OSC integration tests to properly select devices on tracks
- [x] Create browser resources and tools for browser navigation
- [x] Implement browser indexer with ChromaDB vector database
- [x] Add device recommendation based on semantic search
- [x] Add comprehensive browser infrastructure tests

#### Integration Improvements

- [x] Fix app integration tests that use the MCP protocol
- [x] Implement real MCP integration tests with Bitwig Studio
- [x] Improve browser pagination integration tests
- [ ] Ensure MCP server tests work with mock controllers

#### Browser Implementation Status

- [x] **Browser Navigation**

  - [x] Open browser and browse for devices
  - [x] Navigate browser tabs
  - [x] Navigate filters and results
  - [x] Select and commit browser choices

- [x] **Browser State Resources**

  - [x] Access to browser filters and results via URIs
  - [x] Query browser state (active tab, selected items)
  - [x] Read browser filter items and results

- [x] **Device Search Infrastructure**

  - [x] ChromaDB integration for vector database
  - [x] Sentence transformer integration for embeddings
  - [x] Basic device indexing functionality
  - [x] Device recommendation using semantic search

- [ ] **High-Level Resources (Planned)**
  - [ ] Add `bitwig://browser/devices` resource to list available device categories
  - [ ] Add `bitwig://browser/devices/{category}` to list devices in a category
  - [ ] Add `bitwig://browser/presets/{device}` to list available presets
  - [ ] Create device capabilities discovery mechanism

#### Project State Infrastructure (Planned)

- [ ] Add `bitwig://project` resource for overall project metadata
- [ ] Add `bitwig://clips` resource to list all clips in the project
- [ ] Add `bitwig://clip/{id}` resource to access MIDI data
- [ ] Add `bitwig://arrangement` to access arrangement information
- [ ] Implement tools to query and modify project structure

#### Browser Implementation Challenges

The current browser implementation faces several challenges:

- Limited visibility into browser structure via OSC
- Difficulty in programmatically navigating between different device categories
- Challenges with extracting complete metadata for devices
- Issues with OSC responses for some browser addresses

### Priority: Song Creation and Composition Workflows

Based on review of common music production workflows, we're prioritizing song creation and composition capabilities to make Claude most useful for creative tasks. This reflects a standard progression from ideation to finalization in the music creation process.

#### Workflow-Driven Development

Our development priorities are guided by the natural progression of music creation:

1. **Ideation and Composition** - The initial creative phase where musical ideas are formed
2. **Sound Design** - The process of creating and refining the sonic palette
3. **Arrangement** - Organizing musical ideas into a coherent structure
4. **Mixing and Production** - Refining and balancing the sounds to create a polished product

By following this workflow, we ensure that Claude can assist meaningfully at each stage of the music creation process, with a focus on the creative aspects first. This approach enables users to realize their musical ideas more efficiently and effectively.

#### Critical Missing Infrastructure

For Claude to effectively assist with music production, we need to implement two critical components that are currently missing:

1. **Device Browser and Library Access**

   - A comprehensive representation of available Bitwig devices
   - Ability to browse and load devices by category
   - Access to device presets and metadata
   - Mechanism to query device capabilities and parameters
   - Device recommendation system based on semantic search

2. **Project State Representation**
   - Complete overview of the current project structure
   - Access to MIDI clip contents for analysis
   - Arrangement and scene information
   - Project metadata (tempo, key, markers, time signature changes)
   - Ability to query and modify the project state programmatically

These components form the foundation upon which all creative workflows depend, and should be prioritized in the immediate implementation phase.

#### 1. Ideation & Composition Phase (Target: Sprint 1)

- [ ] **MIDI Clip Creation and Editing**

  - [ ] Create new MIDI clips in the arranger
  - [ ] Add/edit notes in MIDI clips
  - [ ] Access and modify note properties (velocity, length, position)
  - [ ] Query clip contents for analysis by Claude

- [ ] **Harmonic Analysis and Suggestion**

  - [ ] Detect and report chord progressions from MIDI clips
  - [ ] Suggest chord progressions based on music theory
  - [ ] Identify key signatures from existing material

- [ ] **Pattern Generation**
  - [ ] Create common rhythm patterns (drums, bass, etc.)
  - [ ] Generate melodic patterns based on chord progressions
  - [ ] Save/recall pattern presets

#### 2. Sound Design Phase (Target: Sprint 1-2)

- [ ] **Instrument and Effect Chain Management**

  - [ ] Browse and load instruments from the library
  - [ ] Create complex instrument/effect chains
  - [ ] Save and recall device presets
  - [ ] Access detailed device parameters

- [ ] **Parameter Automation**
  - [ ] Create automation for device parameters
  - [ ] Design dynamic sound evolution
  - [ ] Generate common automation shapes (LFO, envelope)

#### 3. Arrangement Phase (Target: Sprint 2)

- [ ] **Project Structure Management**

  - [ ] Create arrangements with multiple sections
  - [ ] Duplicate/copy/move sections
  - [ ] Define song structure (intro, verse, chorus, etc.)
  - [ ] Set up transitions between sections

- [ ] **Track Organization**
  - [ ] Create logical groupings of tracks
  - [ ] Set up routing between tracks
  - [ ] Implement send effects configuration

#### 4. Mixing & Production Phase (Target: Sprint 3)

- [ ] **Advanced Mixing Capabilities**

  - [ ] Configure EQ across multiple tracks
  - [ ] Set up compression and dynamics processing
  - [ ] Balance levels across the project
  - [ ] Create stereo image enhancements

- [ ] **Finishing Tools**
  - [ ] Master bus processing controls
  - [ ] Export options for various formats
  - [ ] Preparation for distribution

### Additional Implementation Tasks

#### For Developers (Target: Concurrent with above phases)

1. **Subscription Model**
   - [ ] Implement parameter change subscriptions
   - [ ] Add event-based notification system
   - [ ] Create WebSocket-based event streaming

#### For AI Assistants (Integrated throughout phases)

1. **Context Awareness**

   - [ ] Implement project structure analysis
   - [ ] Add MIDI pattern examination capabilities
   - [ ] Create chord progression analysis tools

2. **Creative Tools**
   - [ ] Add arrangement structure modification tools
   - [ ] Implement clip creation/modification capabilities

#### For Systems Integration (Target: Sprint 3)

1. **External Control**

   - [ ] Implement MIDI controller mapping
   - [ ] Add external trigger capabilities

2. **Automation**
   - [ ] Create task scheduling framework
   - [ ] Implement event-based automation system

### Development Tasks and Next Steps

1. **MCP Improvements**

   - Enhance MCP server with improved error handling and better client session management
   - Develop mock controllers for use in MCP server testing
   - Implement additional MCP tools for advanced Bitwig functionality
   - Ensure compatibility with future MCP protocol changes

2. **Browser Infrastructure Improvements**

   - Continue improving browser indexer to handle different device types (Instruments, Audio FX, Note FX)
   - Enhance device metadata collection to include categories, types, and capabilities
   - Create high-level browser resources for device categories and presets
   - Add semantic search integration in MCP tools

3. **Project State Infrastructure**

   - Start implementing project state resources for arrangement and clip access
   - Add support for querying and modifying MIDI data
   - Create tools for project structure analysis and modification
   - Develop resources for accessing project metadata (tempo, key, markers)

4. **General Improvements**
   - Create additional prompt templates in `prompts.py` for common workflows
   - Enhance error handling for browser and device operations
   - Continue adding comprehensive tests for all new functionality
   - Document browser infrastructure usage
   - Improve API documentation

## Testing

For testing:

- Unit tests are in the `tests/` directory
- Integration tests that check OSC functionality are in `tests/integration/`
- Ensure venv is active
- Run tests with `pytest tests/` or `make test`
