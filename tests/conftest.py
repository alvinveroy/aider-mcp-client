import pytest
import sys
from unittest.mock import MagicMock, AsyncMock

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
