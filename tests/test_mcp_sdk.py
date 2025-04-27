import unittest
import json
import os
import tempfile
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path

from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client

class TestMcpSdkIntegration(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for test configs
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        
        # Default test config
        self.test_config = {
            "mcpServers": {
                "mcp-sdk": {
                    "command": "python",
                    "args": ["-m", "mcp.server.stdio"],
                    "enabled": True,
                    "timeout": 30,
                    "sdk": True
                }
            }
        }
    
    def tearDown(self):
        # Clean up the temporary directory
        self.temp_dir.cleanup()
    
    @patch('mcp.client.stdio.stdio_client')
    @patch('mcp.ClientSession')
    def test_mcp_sdk_connection(self, mock_client_session, mock_stdio_client):
        """Test connection to MCP server using the SDK"""
        # Mock the read and write streams
        mock_read = AsyncMock()
        mock_write = AsyncMock()
        mock_stdio_client.return_value.__aenter__.return_value = (mock_read, mock_write)
        
        # Mock the client session
        mock_session = AsyncMock()
        mock_client_session.return_value.__aenter__.return_value = mock_session
        mock_session.initialize.return_value = {"name": "test-server", "version": "1.0.0"}
        
        # Create a test coroutine to run the async code
        async def test_coro():
            # Create server parameters
            server_params = StdioServerParameters(
                command="python",
                args=["-m", "mcp.server.stdio"],
                env=None,
            )
            
            # Connect to the server
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    # Initialize the connection
                    init_result = await session.initialize()
                    return init_result
        
        # Run the test coroutine
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(test_coro())
        
        # Verify the connection was initialized
        self.assertEqual(result, {"name": "test-server", "version": "1.0.0"})
        mock_session.initialize.assert_called_once()
    
    @patch('mcp.client.stdio.stdio_client')
    @patch('mcp.ClientSession')
    def test_mcp_sdk_list_tools(self, mock_client_session, mock_stdio_client):
        """Test listing tools from MCP server using the SDK"""
        # Mock the read and write streams
        mock_read = AsyncMock()
        mock_write = AsyncMock()
        mock_stdio_client.return_value.__aenter__.return_value = (mock_read, mock_write)
        
        # Mock the client session
        mock_session = AsyncMock()
        mock_client_session.return_value.__aenter__.return_value = mock_session
        mock_session.list_tools.return_value = [
            types.Tool(
                name="resolve-library-id",
                description="Resolves a library name to its ID",
                arguments=[
                    types.ToolArgument(
                        name="libraryName",
                        description="Name of the library to resolve",
                        required=True,
                        type="string"
                    )
                ]
            )
        ]
        
        # Create a test coroutine to run the async code
        async def test_coro():
            # Create server parameters
            server_params = StdioServerParameters(
                command="python",
                args=["-m", "mcp.server.stdio"],
                env=None,
            )
            
            # Connect to the server
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    # List tools
                    tools = await session.list_tools()
                    return tools
        
        # Run the test coroutine
        loop = asyncio.get_event_loop()
        tools = loop.run_until_complete(test_coro())
        
        # Verify the tools were listed
        self.assertEqual(len(tools), 1)
        self.assertEqual(tools[0].name, "resolve-library-id")
        mock_session.list_tools.assert_called_once()
    
    @patch('mcp.client.stdio.stdio_client')
    @patch('mcp.ClientSession')
    def test_mcp_sdk_call_tool(self, mock_client_session, mock_stdio_client):
        """Test calling a tool on MCP server using the SDK"""
        # Mock the read and write streams
        mock_read = AsyncMock()
        mock_write = AsyncMock()
        mock_stdio_client.return_value.__aenter__.return_value = (mock_read, mock_write)
        
        # Mock the client session
        mock_session = AsyncMock()
        mock_client_session.return_value.__aenter__.return_value = mock_session
        mock_session.call_tool.return_value = {"result": "react/react"}
        
        # Create a test coroutine to run the async code
        async def test_coro():
            # Create server parameters
            server_params = StdioServerParameters(
                command="python",
                args=["-m", "mcp.server.stdio"],
                env=None,
            )
            
            # Connect to the server
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    # Call a tool
                    result = await session.call_tool(
                        "resolve-library-id", 
                        arguments={"libraryName": "react"}
                    )
                    return result
        
        # Run the test coroutine
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(test_coro())
        
        # Verify the tool was called
        self.assertEqual(result, {"result": "react/react"})
        mock_session.call_tool.assert_called_once_with(
            "resolve-library-id", 
            arguments={"libraryName": "react"}
        )

if __name__ == "__main__":
    unittest.main()
