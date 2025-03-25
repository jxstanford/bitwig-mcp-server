"""
Tests for the Bitwig MCP Server settings module.
"""

import logging
import os
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from bitwig_mcp_server.settings import Settings, get_settings


def test_settings_defaults():
    """Test that settings have the expected defaults."""
    settings = Settings()

    # Check default values
    assert settings.app_name == "bitwig-mcp-server"
    assert settings.app_tagline == "MCP server for Bitwig Studio."
    assert settings.log_level == "INFO"
    assert settings.bitwig_host == "127.0.0.1"
    assert settings.bitwig_send_port == 8000
    assert settings.bitwig_receive_port == 9000
    assert settings.mcp_port == 8080


def test_settings_validation():
    """Test that settings validation works as expected."""
    # Test invalid log level
    with pytest.raises(ValidationError, match="log_level must be one of"):
        Settings(log_level="INVALID")

    # Test empty app name
    with pytest.raises(ValidationError, match="app_name must not be empty"):
        Settings(app_name="")


def test_settings_env_vars():
    """Test that settings are loaded from environment variables."""
    # Patch environment variables
    env_vars = {
        "BITWIG_MCP_APP_NAME": "custom-server",
        "BITWIG_MCP_LOG_LEVEL": "DEBUG",
        "BITWIG_MCP_BITWIG_HOST": "192.168.1.100",
        "BITWIG_MCP_BITWIG_SEND_PORT": "8001",
        "BITWIG_MCP_BITWIG_RECEIVE_PORT": "9001",
        "BITWIG_MCP_MCP_PORT": "8081",
    }

    with patch.dict(os.environ, env_vars):
        settings = Settings()

        # Check that environment variables were applied
        assert settings.app_name == "custom-server"
        assert settings.log_level == "DEBUG"
        assert settings.bitwig_host == "192.168.1.100"
        assert settings.bitwig_send_port == 8001
        assert settings.bitwig_receive_port == 9001
        assert settings.mcp_port == 8081


def test_get_settings():
    """Test get_settings function."""
    with patch("bitwig_mcp_server.settings.Settings") as mock_settings_class:
        mock_settings = mock_settings_class.return_value
        mock_settings.configure_logging = lambda: None

        settings = get_settings()

        # Check that Settings was called and configure_logging was called
        mock_settings_class.assert_called_once()
        assert settings == mock_settings


def test_settings_configure_logging():
    """Test the configure_logging method."""
    with patch("logging.basicConfig") as mock_logging:
        settings = Settings(log_level="DEBUG")
        settings.configure_logging()

        # Check that logging was configured with the correct level
        mock_logging.assert_called_once()
        args, kwargs = mock_logging.call_args
        assert kwargs["level"] == logging.DEBUG


def test_env_file_path():
    """Test the env_file_path property."""
    settings = Settings()

    # Test when .env exists
    with patch.object(Path, "exists", return_value=True):
        assert settings.env_file_path is not None
        assert settings.env_file_path.name == ".env"

    # Test when .env doesn't exist
    with patch.object(Path, "exists", return_value=False):
        assert settings.env_file_path is None
