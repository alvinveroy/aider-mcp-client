import unittest
import asyncio
from unittest.mock import patch, MagicMock
from aider_mcp_client.mcp_sdk_client import resolve_library_id_sdk, fetch_documentation_sdk

class TestMcpExample(unittest.TestCase):
    """Test the example MCP client implementation."""
    
    @patch('aider_mcp_client.mcp_sdk_client.call_mcp_tool')
    def test_resolve_library_id_sdk(self, mock_call_tool):
        """Test resolving library ID using the SDK client."""
        # Mock the response from the MCP server
        mock_call_tool.return_value = {"libraryId": "vercel/nextjs"}
        
        # Create a test coroutine to run the async code
        async def test_coro():
            result = await resolve_library_id_sdk("next.js")
            self.assertEqual(result, "vercel/nextjs")
            mock_call_tool.assert_called_once_with(
                command="npx",
                args=["-y", "@upstash/context7-mcp@latest"],
                tool_name="resolve-library-id",
                tool_args={"libraryName": "next.js"},
                timeout=30
            )
        
        # Run the test coroutine
        asyncio.run(test_coro())
    
    @patch('aider_mcp_client.mcp_sdk_client.call_mcp_tool')
    def test_fetch_documentation_sdk(self, mock_call_tool):
        """Test fetching documentation using the SDK client."""
        # Mock the response from the MCP server
        mock_response = {
            "content": "Sample documentation for Next.js routing",
            "library": "vercel/nextjs",
            "snippets": [],
            "totalTokens": 1000,
            "lastUpdated": "2023-01-01"
        }
        mock_call_tool.return_value = mock_response
        
        # Create a test coroutine to run the async code
        async def test_coro():
            result = await fetch_documentation_sdk(
                library_id="vercel/nextjs",
                topic="routing",
                tokens=1000
            )
            self.assertEqual(result, mock_response)
            mock_call_tool.assert_called_once_with(
                command="npx",
                args=["-y", "@upstash/context7-mcp@latest"],
                tool_name="get-library-docs",
                tool_args={
                    "context7CompatibleLibraryID": "vercel/nextjs",
                    "topic": "routing",
                    "tokens": 5000  # Note: The function ensures a minimum of 5000 tokens
                },
                timeout=30
            )
        
        # Run the test coroutine
        asyncio.run(test_coro())

if __name__ == '__main__':
    unittest.main()
