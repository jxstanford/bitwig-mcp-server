"""
Tests for the main application module.
"""

from unittest.mock import AsyncMock, patch

import pytest

from bitwig_mcp_server.app import main


@pytest.mark.asyncio
async def test_run_server_mock():
    """Test that run_server is called from main()."""
    with (
        patch("bitwig_mcp_server.app.run_server", new_callable=AsyncMock),
        patch("bitwig_mcp_server.app.asyncio.run") as mock_asyncio_run,
    ):
        # Call main
        result = main()

        # Verify asyncio.run was called with run_server
        mock_asyncio_run.assert_called_once()
        assert result == 0


def test_main_keyboard_interrupt():
    """Test main() handling KeyboardInterrupt."""
    with patch("bitwig_mcp_server.app.asyncio.run", side_effect=KeyboardInterrupt):
        result = main()
        assert result == 0


def test_main_exception():
    """Test main() handling general exceptions."""
    with patch(
        "bitwig_mcp_server.app.asyncio.run", side_effect=Exception("Test error")
    ):
        result = main()
        assert result == 1
