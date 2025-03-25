"""
Bitwig MCP Server

Application entry point for the Bitwig Studio MCP integration.
This module coordinates the MCP server and provides a CLI interface.
"""

import asyncio
import logging
import sys

from bitwig_mcp_server.mcp.server import run_server

# Set up logging
logger = logging.getLogger(__name__)


def main() -> int:
    """Main entry point

    Returns:
        Exit code
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    try:
        asyncio.run(run_server())
        return 0
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        return 0
    except Exception as e:
        logger.exception(f"Server terminated with error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
