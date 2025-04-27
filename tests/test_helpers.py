"""
Helper functions for testing the MCP client.
"""

import asyncio
import os
import sys
from unittest.mock import patch, MagicMock

def is_ci_environment():
    """Check if we're running in a CI environment."""
    return os.environ.get('CI') == 'true' or os.environ.get('GITHUB_ACTIONS') == 'true'

def patch_asyncio_for_tests():
    """Patch asyncio to avoid 'Event loop is closed' errors in tests."""
    # Create a new event loop policy that doesn't close loops
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    else:
        asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())
    
    # Create a new event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Return the loop so it can be closed properly
    return loop

def run_async_test(coro):
    """Run an async test function."""
    loop = patch_asyncio_for_tests()
    try:
        return loop.run_until_complete(coro)
    finally:
        try:
            loop.close()
        except:
            pass
