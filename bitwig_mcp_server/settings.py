import logging
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_default_root_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def get_default_env_file() -> Path:
    env_file = get_default_root_dir() / ".env"
    if not env_file.exists():
        logger.warning(f"{env_file} does not exist")
    return env_file


class Settings(BaseSettings):
    """
    Settings class.

    Attributes:
        app_name (str): The name of the application.
        app_logo_image (Path): The path to the application logo image.
        app_tagline (str): The tagline of the application.
        root_dir (Path): The root directory of the application.
        log_level (str): The logging level (e.g., ERROR, WARN, INFO, DEBUG).
        bitwig_host (str): The hostname or IP address of the Bitwig Studio instance.
        bitwig_send_port (int): The port to send OSC messages to Bitwig.
        bitwig_receive_port (int): The port to receive OSC messages from Bitwig.
        mcp_port (int): The port for the MCP server's HTTP/SSE transport.
    """

    app_name: str = "bitwig-mcp-server"
    app_tagline: str = "MCP server for Bitwig Studio."
    root_dir: Path = Field(default_factory=get_default_root_dir)
    app_logo_image: Path = Field(
        default_factory=lambda: get_default_root_dir() / "logo.jpg"
    )
    log_level: str = Field(default="INFO", description="The logging level.")

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
        """
        Configuration class for Settings.

        Attributes:
            env_file (str): The name of the environment file to load settings from.
            env_file_encoding (str): The encoding of the environment file.
        """

        env_file = get_default_env_file()
        env_file_encoding = "utf-8"

    @field_validator("app_name")
    def validate_str_not_empty(cls, v: str) -> str:
        if isinstance(v, str) and not v.strip():
            raise ValueError("app_name must not be empty")
        return v

    @field_validator("log_level")
    def validate_log_level(cls, v: str) -> str:
        if v.upper() not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            raise ValueError(
                "log_level must be one of DEBUG, INFO, WARNING, ERROR", "CRITICAL"
            )
        return v

    @field_validator("root_dir")
    def validate_path_exists(cls, v: Path) -> Path:
        if not v.exists():
            raise ValueError(f"{v} does not exist")
        return v
