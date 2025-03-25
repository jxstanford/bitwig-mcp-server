"""
Settings configuration for the Bitwig MCP Server.

This module provides configuration settings using Pydantic for validation.
"""

import logging
from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """
    Application settings with validation.

    Attributes:
        app_name (str): The application name identifier.
        app_logo_image (Path): The path to the application logo image.
        app_tagline (str): The application tagline/description.
        root_dir (Path): The root directory of the application.
        log_level (str): The logging level (e.g., ERROR, WARN, INFO, DEBUG).
        bitwig_host (str): The hostname or IP address of the Bitwig Studio instance.
        bitwig_send_port (int): The port to send OSC messages to Bitwig.
        bitwig_receive_port (int): The port to receive OSC messages from Bitwig.
        mcp_port (int): The port for the MCP server's HTTP/SSE transport.
    """

    app_name: str = "bitwig-mcp-server"
    app_tagline: str = "MCP server for Bitwig Studio."
    root_dir: Path = Field(
        default_factory=lambda: Path(__file__).resolve().parent.parent
    )
    app_logo_image: Path = Field(
        default_factory=lambda: Path(__file__).resolve().parent.parent / "logo.jpg"
    )
    log_level: str = Field("INFO", description="The logging level.")

    # Bitwig settings
    bitwig_host: str = Field(
        default="127.0.0.1", description="Bitwig Studio host address"
    )
    bitwig_send_port: int = Field(
        default=8000, description="Port to send OSC messages to Bitwig"
    )
    bitwig_receive_port: int = Field(
        default=9000, description="Port to receive OSC messages from Bitwig"
    )

    # MCP settings
    mcp_port: int = Field(
        default=8080, description="Port for MCP server HTTP/SSE transport"
    )

    class Config:
        """Configuration for settings behavior."""

        env_file = ".env"
        env_file_encoding = "utf-8"
        env_prefix = "BITWIG_MCP_"
        case_sensitive = False

    @field_validator("log_level")
    def validate_log_level(cls, v: str) -> str:
        """Validate the log level is a recognized value.

        Args:
            v: The log level value

        Returns:
            The validated log level

        Raises:
            ValueError: If log level is not valid
        """
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"log_level must be one of {', '.join(valid_levels)}")
        return v.upper()

    @field_validator("app_name")
    def validate_app_name(cls, v: str) -> str:
        """Validate the app name is not empty.

        Args:
            v: The app name value

        Returns:
            The validated app name

        Raises:
            ValueError: If app name is empty
        """
        if not v.strip():
            raise ValueError("app_name must not be empty")
        return v

    def configure_logging(self) -> None:
        """Configure logging based on settings."""
        log_level = getattr(logging, self.log_level)
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        logger.info(f"Logging configured with level {self.log_level}")

    @property
    def env_file_path(self) -> Optional[Path]:
        """Get the path to the loaded .env file.

        Returns:
            Path to the .env file if it exists, None otherwise
        """
        env_file = self.root_dir / self.Config.env_file
        return env_file if env_file.exists() else None


def get_settings() -> Settings:
    """Get application settings from environment.

    Returns:
        Configured Settings instance
    """
    try:
        settings = Settings()
        settings.configure_logging()
        return settings
    except Exception as e:
        logger.error(f"Error loading settings: {e}")
        raise
