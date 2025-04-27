"""
Helper functions for testing the MCP client.
"""

import asyncio
import os
import sys
from unittest.mock import patch, MagicMock, AsyncMock

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
    """Run an async test function safely."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    except RuntimeError as e:
        if "Event loop is closed" in str(e):
            # Create a new loop if the current one is closed
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(coro)
        raise

def mock_stdio_client():
    """Create a properly mocked stdio_client for tests."""
    mock = AsyncMock()
    # Make the return value of __aenter__ a tuple of AsyncMocks
    read_mock = AsyncMock()
    write_mock = AsyncMock()
    mock.return_value.__aenter__.return_value = (read_mock, write_mock)
    return mock
