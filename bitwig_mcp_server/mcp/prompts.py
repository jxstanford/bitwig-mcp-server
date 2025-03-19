"""
Bitwig MCP Prompts

MCP prompt template implementations for Bitwig Studio integration.
"""

from typing import Optional

from mcp.types import Prompt, PromptArgument, PromptMessage, TextContent, Role


class BitwigPrompts:
    """Helper for Bitwig-specific MCP prompt templates"""

    @staticmethod
    def list_prompts() -> list[Prompt]:
        """Get a list of all available Bitwig prompts"""
        return [
            Prompt(
                name="setup_mixing_session",
                description="Set up a new mixing session with default settings",
                arguments=[
                    PromptArgument(
                        name="num_tracks",
                        description="Number of tracks to create",
                        required=False,
                    )
                ],
            ),
            Prompt(
                name="create_track_template",
                description="Create a track template with specific devices and settings",
                arguments=[
                    PromptArgument(
                        name="track_type",
                        description="Type of track (e.g., drums, bass, vocals)",
                        required=True,
                    ),
                    PromptArgument(
                        name="genre",
                        description="Musical genre for optimizing presets",
                        required=False,
                    ),
                ],
            ),
            Prompt(
                name="optimize_track_settings",
                description="Get recommendations for optimizing track settings",
                arguments=[
                    PromptArgument(
                        name="track_type",
                        description="Type of track (e.g., drums, bass, vocals)",
                        required=True,
                    ),
                    PromptArgument(
                        name="problem",
                        description="Specific problem to address (e.g., muddy, harsh, thin)",
                        required=False,
                    ),
                ],
            ),
        ]

    @staticmethod
    def get_prompt(
        name: str, arguments: Optional[dict[str, str]] = None
    ) -> list[PromptMessage]:
        """Get a specific prompt template with arguments filled in"""
        if arguments is None:
            arguments = {}

        if name == "setup_mixing_session":
            num_tracks = arguments.get("num_tracks", "8")
            return [
                PromptMessage(
                    role=Role.USER,
                    content=TextContent(
                        type="text",
                        text=f"""I want to set up a new mixing session in Bitwig Studio.

Here's what I need help with:
1. Creating a balanced mix template with {num_tracks} tracks
2. Setting up appropriate sends for reverb and delay
3. Configuring monitor output and gain staging
4. Setting up basic mastering chain on the master track

Can you help me set this up step by step?""",
                    ),
                )
            ]

        elif name == "create_track_template":
            track_type = arguments.get("track_type", "")
            genre = arguments.get("genre", "general")

            return [
                PromptMessage(
                    role=Role.USER,
                    content=TextContent(
                        type="text",
                        text=f"""I need to create a template for a {track_type} track in Bitwig Studio for {genre} music.

Please help me with:
1. What devices should I add to this track type?
2. What settings and parameters would work well for this type of track?
3. How should I set up the routing and monitoring?
4. Are there any specific EQ or compression settings that would work well?

Can you provide detailed step-by-step guidance?""",
                    ),
                )
            ]

        elif name == "optimize_track_settings":
            track_type = arguments.get("track_type", "")
            problem = arguments.get("problem", "general balance")

            return [
                PromptMessage(
                    role=Role.USER,
                    content=TextContent(
                        type="text",
                        text=f"""I'm having issues with my {track_type} track in Bitwig Studio. The specific problem is that it sounds {problem}.

Can you help me:
1. Identify common causes for this issue with this type of track
2. Suggest parameter adjustments for EQ, compression, and other processing
3. Recommend specific Bitwig devices and settings to address the problem
4. Propose a step-by-step approach to fix the issue

Please give me detailed settings I can try.""",
                    ),
                )
            ]

        else:
            raise ValueError(f"Unknown prompt: {name}")
