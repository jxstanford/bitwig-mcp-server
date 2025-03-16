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

    """

    app_name: str = "bitwig-mcp-server"
    app_tagline: str = "MCP server for Bitwig Studio."
    root_dir: Path = Field(default_factory=get_default_root_dir)
    app_logo_image: Path = Field(default_factory=lambda: get_default_root_dir() / "logo.jpg")
    log_level: str = Field(default="INFO", description="The logging level.")

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
            raise ValueError("log_level must be one of DEBUG, INFO, WARNING, ERROR", "CRITICAL")
        return v

    @field_validator("root_dir")
    def validate_path_exists(cls, v: Path) -> Path:
        if not v.exists():
            raise ValueError(f"{v} does not exist")
        return v
