import pytest
import sys
import os
import asyncio
from unittest.mock import MagicMock, AsyncMock

# Set test mode environment variable
os.environ['AIDER_MCP_TEST_MODE'] = 'true'

# Create a fixture to handle event loop issues
@pytest.fixture(scope="session", autouse=True)
def event_loop_fixture():
    """Create and set a new event loop for all tests."""
    # Create a new event loop
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    else:
        asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    yield loop
    
    # Clean up
    try:
        loop.close()
    except:
        pass

# Create mock classes for the mcp module
class MockClientSession:
    def __init__(self, *args, **kwargs):
        pass
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, *args):
        pass
    
    async def initialize(self):
        pass
    
    async def list_tools(self):
        pass
    
    async def call_tool(self, *args, **kwargs):
        pass

class MockStdioServerParameters:
    def __init__(self, command, args, env):
        self.command = command
        self.args = args
        self.env = env

class MockToolArgument:
    def __init__(self, name, description, required, type):
        self.name = name
        self.description = description
        self.required = required
        self.type = type

class MockTool:
    def __init__(self, name, description, arguments):
        self.name = name
        self.description = description
        self.arguments = arguments

# Create mock modules
mock_types = MagicMock()
mock_types.Tool = MockTool
mock_types.ToolArgument = MockToolArgument

# Setup mock for mcp module
@pytest.fixture(autouse=True)
def mock_mcp_module():
    """Mock the mcp module for all tests."""
    mcp_mock = MagicMock()
    mcp_mock.ClientSession = MockClientSession
    mcp_mock.StdioServerParameters = MockStdioServerParameters
    mcp_mock.types = mock_types
    
    mcp_client_stdio_mock = MagicMock()
    mcp_client_stdio_mock.stdio_client = AsyncMock()
    
    with pytest.MonkeyPatch.context() as mp:
        mp.setitem(sys.modules, 'mcp', mcp_mock)
        mp.setitem(sys.modules, 'mcp.client.stdio', mcp_client_stdio_mock)
        yield
