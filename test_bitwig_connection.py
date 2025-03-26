#!/usr/bin/env python
"""Test script to check if Bitwig Studio is running and available via OSC."""

import asyncio
import logging
import sys

from bitwig_mcp_server.osc.controller import BitwigOSCController

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


async def test_connection():
    """Test the connection to Bitwig Studio."""
    controller = None
    try:
        logger.info("Initializing OSC controller...")
        controller = BitwigOSCController()

        # Wait for controller to initialize
        await asyncio.sleep(2)

        # Test if client is available
        if not controller.client:
            logger.error(
                "❌ Could not connect to Bitwig Studio: OSC client not available"
            )
            return False

        # Start the controller (which isn't automatically started in the constructor)
        try:
            controller.start()
            await asyncio.sleep(1.0)
        except Exception as e:
            logger.error(f"❌ Failed to start controller: {e}")
            return False

        # Try to get a basic response from Bitwig
        logger.info("Attempting to communicate with Bitwig Studio...")

        # Send a refresh command
        controller.client.refresh()
        await asyncio.sleep(1)

        # Try to get current tempo
        tempo = controller.server.get_message("/transport/tempo")
        logger.info(f"Project tempo: {tempo}")

        if tempo is not None:
            logger.info("✅ Successfully connected to Bitwig Studio")
            return True
        else:
            logger.error("❌ Connected but not receiving data from Bitwig Studio")
            logger.error("Please ensure Bitwig Studio is running with a project open")
            logger.error("and that OSC is enabled in Bitwig settings.")
            return False

    except Exception as e:
        logger.error(f"❌ Error connecting to Bitwig Studio: {e}")
        return False
    finally:
        # Cleanup
        if controller is not None:
            try:
                await controller.stop()
            except Exception as e:
                logger.error(f"Error stopping controller: {e}")


if __name__ == "__main__":
    result = asyncio.run(test_connection())
    sys.exit(0 if result else 1)
