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
            # Force the mock to be called by setting _is_test=True
            with patch('os.environ.get') as mock_env:
                mock_env.return_value = None  # Make sure AIDER_MCP_TEST_MODE is not set
                with patch('sys.modules', {}):  # Make sure unittest is not in sys.modules
                    result = await resolve_library_id_sdk("next.js", _is_test=True)
                    self.assertEqual(result, "vercel/nextjs")
                    mock_call_tool.assert_called_once_with(
                        command="npx",
                        args=["-y", "@upstash/context7-mcp@latest"],
                        tool_name="resolve-library-id",
                        tool_args={"libraryName": "next.js"},
                        timeout=30,
                        new_event_loop=False,
                        _is_test=True
                    )
        
        # Run the test coroutine
        from tests.test_helpers import run_async_test
        run_async_test(test_coro())
    
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
            # Force the mock to be called by setting _is_test=True
            with patch('os.environ.get') as mock_env:
                mock_env.return_value = None  # Make sure AIDER_MCP_TEST_MODE is not set
                with patch('sys.modules', {}):  # Make sure unittest is not in sys.modules
                    result = await fetch_documentation_sdk(
                        library_id="vercel/nextjs",
                        topic="routing",
                        tokens=1000,
                        _is_test=True
                    )
                    self.assertEqual(result, mock_response)
                    mock_call_tool.assert_called_once_with(
                        command="npx",
                        args=["-y", "@upstash/context7-mcp@latest"],
                        tool_name="get-library-docs",
                        tool_args={
                            "context7CompatibleLibraryID": "vercel/nextjs",
                            "topic": "routing",
                            "tokens": 1000  # Use the value passed to the function
                        },
                        timeout=60,  # The fetch_documentation_sdk function uses a 60 second timeout
                        new_event_loop=False,
                        _is_test=True
                    )
        
        # Run the test coroutine
        from tests.test_helpers import run_async_test
        run_async_test(test_coro())

if __name__ == '__main__':
    unittest.main()
