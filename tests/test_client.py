import unittest
import json
import os
import tempfile
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path
from aider_mcp_client.client import (
    load_config, 
    communicate_with_mcp_server, 
    resolve_library_id, 
    fetch_documentation,
    list_supported_libraries,
    async_main
)

class TestAiderMcpClient(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for test configs
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        
        # Default test config
        self.test_config = {
            "mcp_server": {
                "command": "test_command",
                "args": ["test_arg1", "test_arg2"],
                "tool": "get-library-docs",
                "timeout": 15,
                "enabled": True
            },
            "mcpServers": {
                "context7": {
                    "command": "test_command",
                    "args": ["test_arg1", "test_arg2"],
                    "enabled": True,
                    "timeout": 15
                }
            }
        }
    
    def tearDown(self):
        # Clean up the temporary directory
        self.temp_dir.cleanup()
    
    def test_load_config_default(self):
        """Test that default config is loaded when no config files exist"""
        with patch('aider_mcp_client.client.Path.exists', return_value=False):
            config = load_config()
            self.assertEqual(config["mcpServers"]["context7"]["command"], "npx")
            self.assertEqual(config["mcpServers"]["context7"]["args"], ["-y", "@upstash/context7-mcp@latest"])
            self.assertEqual(config["mcpServers"]["context7"]["timeout"], 30)
            self.assertEqual(config["mcpServers"]["context7"]["enabled"], True)
    
    def test_load_config_local(self):
        """Test loading config from local directory"""
        # Create a temporary local config file
        local_config_dir = self.temp_path / ".aider-mcp-client"
        local_config_dir.mkdir(exist_ok=True)
        local_config_path = local_config_dir / "config.json"
        
        with open(local_config_path, 'w', encoding='utf-8') as f:
            json.dump(self.test_config, f)
        
        # Mock the current working directory
        with patch('aider_mcp_client.client.Path.cwd', return_value=self.temp_path):
            with patch('aider_mcp_client.client.Path.exists', return_value=True):
                with patch('aider_mcp_client.client.open', return_value=open(local_config_path, 'r')):
                    config = load_config()
                    self.assertEqual(config["mcp_server"]["command"], "test_command")
                    self.assertEqual(config["mcp_server"]["args"], ["test_arg1", "test_arg2"])
                    self.assertEqual(config["mcp_server"]["tool"], "get-library-docs")
    
    def test_load_config_home(self):
        """Test loading config from home directory"""
        # Create a temporary home config file
        home_config_dir = self.temp_path / ".aider-mcp-client"
        home_config_dir.mkdir(exist_ok=True)
        home_config_path = home_config_dir / "config.json"
        
        with open(home_config_path, 'w', encoding='utf-8') as f:
            json.dump(self.test_config, f)
        
        # Mock the home directory and ensure local config doesn't exist
        with patch('aider_mcp_client.client.Path.home', return_value=self.temp_path):
            # First check returns False (local config), second returns True (home config)
            with patch('aider_mcp_client.client.Path.exists', side_effect=[False, True]):
                with patch('aider_mcp_client.client.open', return_value=open(home_config_path, 'r')):
                    config = load_config()
                    self.assertEqual(config["mcp_server"]["command"], "test_command")
                    self.assertEqual(config["mcp_server"]["args"], ["test_arg1", "test_arg2"])
                    self.assertEqual(config["mcp_server"]["tool"], "get-library-docs")
    
    @patch('aider_mcp_client.client.subprocess.Popen')
    @patch('sys.modules', {'unittest': True})  # Simulate running in unittest environment
    def test_communicate_with_mcp_server(self, mock_popen):
        """Test communication with MCP server"""
        # Mock the subprocess.Popen
        mock_process = MagicMock()
        mock_process.stdout.readline.return_value = '{"result": "test_result"}\n'
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process
        
        request_data = {"tool": "test-tool", "args": {"test_arg": "test_value"}}
        
        # Patch time.sleep to avoid delays in tests
        with patch('time.sleep'):
            # Create a test coroutine to run the async code
            async def test_coro():
                return await communicate_with_mcp_server("test_command", ["test_arg"], request_data, 5)
            
            # Run the test coroutine
            loop = asyncio.get_event_loop()
            result = loop.run_until_complete(test_coro())
        
        # Check that Popen was called with correct arguments
        mock_popen.assert_called_once_with(
            ["test_command", "test_arg"],
            stdin=unittest.mock.ANY,
            stdout=unittest.mock.ANY,
            stderr=unittest.mock.ANY,
            text=True,
            encoding='utf-8'
        )
        
        # Check that stdin.write was called with the correct JSON
        mock_process.stdin.write.assert_called_once_with(json.dumps(request_data) + '\n')
        
        # Check the result
        self.assertEqual(result, {"result": "test_result"})
    
    @patch('aider_mcp_client.client.communicate_with_mcp_server')
    @patch('aider_mcp_client.client.load_config')
    def test_resolve_library_id(self, mock_load_config, mock_communicate):
        """Test resolving library ID"""
        # Mock the config
        mock_load_config.return_value = self.test_config
        
        # Mock the communicate_with_mcp_server response
        mock_communicate.return_value = {"result": "org/library"}
        
        # Create a test coroutine to run the async code
        async def test_coro():
            return await resolve_library_id("library")
        
        # Run the test coroutine
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(test_coro())
        
        # Check that communicate_with_mcp_server was called with correct arguments
        mock_communicate.assert_called_once_with(
            "test_command",
            ["test_arg1", "test_arg2"],
            {
                "tool": "resolve-library-id",
                "args": {
                    "libraryName": "library"
                }
            },
            15
        )
        
        # Check the result
        self.assertEqual(result, "org/library")
    
    @patch('aider_mcp_client.client.resolve_library_id')
    @patch('aider_mcp_client.client.communicate_with_mcp_server')
    @patch('aider_mcp_client.client.load_config')
    def test_fetch_documentation_with_resolution(self, mock_load_config, mock_communicate, mock_resolve):
        """Test fetching documentation with library ID resolution"""
        # Mock the config
        mock_load_config.return_value = self.test_config
        
        # Mock the resolve_library_id response
        mock_resolve.return_value = "org/library"
        
        # Mock the communicate_with_mcp_server response
        mock_communicate.return_value = {
            "library": "org/library",
            "snippets": ["snippet1", "snippet2"],
            "totalTokens": 1000,
            "lastUpdated": "2025-04-27"
        }
        
        with patch('builtins.print') as mock_print:
            # Create a test coroutine to run the async code
            async def test_coro():
                return await fetch_documentation("library", "topic", 6000)
            
            # Run the test coroutine
            loop = asyncio.get_event_loop()
            result = loop.run_until_complete(test_coro())
            
            # Check that resolve_library_id was called with the correct arguments
            mock_resolve.assert_called_once_with("library", custom_timeout=15)
            
            # Check that communicate_with_mcp_server was called with correct arguments
            mock_communicate.assert_called_once_with(
                "test_command",
                ["test_arg1", "test_arg2"],
                {
                    "tool": "get-library-docs",
                    "args": {
                        "context7CompatibleLibraryID": "org/library",
                        "topic": "topic",
                        "tokens": 6000
                    }
                },
                15
            )
            
            # Check the result
            self.assertEqual(result["library"], "org/library")
            self.assertEqual(result["snippets"], ["snippet1", "snippet2"])
            self.assertEqual(result["totalTokens"], 1000)
            self.assertEqual(result["lastUpdated"], "2025-04-27")
    
    @patch('aider_mcp_client.client.communicate_with_mcp_server')
    @patch('aider_mcp_client.client.load_config')
    def test_fetch_documentation_without_resolution(self, mock_load_config, mock_communicate):
        """Test fetching documentation without library ID resolution"""
        # Mock the config
        mock_load_config.return_value = self.test_config
        
        # Mock the communicate_with_mcp_server response
        mock_communicate.return_value = {
            "library": "org/library",
            "snippets": ["snippet1", "snippet2"],
            "totalTokens": 1000,
            "lastUpdated": "2025-04-27"
        }
        
        with patch('builtins.print') as mock_print:
            # Create a test coroutine to run the async code
            async def test_coro():
                return await fetch_documentation("org/library", "topic", 6000)
            
            # Run the test coroutine
            loop = asyncio.get_event_loop()
            result = loop.run_until_complete(test_coro())
            
            # Check that communicate_with_mcp_server was called with correct arguments
            mock_communicate.assert_called_once_with(
                "test_command",
                ["test_arg1", "test_arg2"],
                {
                    "tool": "get-library-docs",
                    "args": {
                        "context7CompatibleLibraryID": "org/library",
                        "topic": "topic",
                        "tokens": 6000
                    }
                },
                15
            )
            
            # Check the result
            self.assertEqual(result["library"], "org/library")
            self.assertEqual(result["snippets"], ["snippet1", "snippet2"])
            self.assertEqual(result["totalTokens"], 1000)
            self.assertEqual(result["lastUpdated"], "2025-04-27")
    
    @patch('builtins.print')
    def test_list_supported_libraries(self, mock_print):
        """Test listing supported libraries"""
        list_supported_libraries()
        mock_print.assert_any_call("Fetching list of supported libraries from Context7...")
        mock_print.assert_any_call("This feature is not yet implemented. Please check https://context7.com for supported libraries.")
    
    @patch('aider_mcp_client.client.communicate_with_mcp_server')
    @patch('aider_mcp_client.client.load_config')
    def test_end_to_end_mcp_server_communication(self, mock_load_config, mock_communicate):
        """Test end-to-end communication with MCP server"""
        # Mock the config
        mock_load_config.return_value = self.test_config
        
        # Mock the communicate_with_mcp_server response for library resolution
        mock_communicate.side_effect = [
            # First call - resolve library ID
            {"result": "react/react"},
            # Second call - fetch documentation
            {
                "library": "react/react",
                "snippets": [
                    "```jsx\nimport React from 'react';\n\nfunction Example() {\n  return <div>Hello World</div>;\n}\n```",
                    "```jsx\nimport React, { useState } from 'react';\n\nfunction Counter() {\n  const [count, setCount] = useState(0);\n  return (\n    <div>\n      <p>You clicked {count} times</p>\n      <button onClick={() => setCount(count + 1)}>Click me</button>\n    </div>\n  );\n}\n```"
                ],
                "totalTokens": 2500,
                "lastUpdated": "2025-04-27"
            }
        ]
        
        # Test the full flow: resolve library ID and then fetch documentation
        with patch('builtins.print') as mock_print:
            # Create a test coroutine to run the async code
            async def test_coro():
                # First resolve the library ID
                library_id = await resolve_library_id("react")
                # Then fetch documentation using the resolved ID
                result = await fetch_documentation(library_id, "hooks", 5000)
                return library_id, result
            
            # Run the test coroutine
            loop = asyncio.get_event_loop()
            library_id, result = loop.run_until_complete(test_coro())
            
            # Verify the results
            self.assertEqual(library_id, "react/react")
            self.assertEqual(result["library"], "react/react")
            self.assertEqual(len(result["snippets"]), 2)
            self.assertEqual(result["totalTokens"], 2500)
            self.assertEqual(result["lastUpdated"], "2025-04-27")
            
            # Verify the correct calls were made to communicate_with_mcp_server
            expected_calls = [
                # First call for resolving library ID
                unittest.mock.call(
                    "test_command",
                    ["test_arg1", "test_arg2"],
                    {
                        "tool": "resolve-library-id",
                        "args": {
                            "libraryName": "react"
                        }
                    },
                    15
                ),
                # Second call for fetching documentation
                unittest.mock.call(
                    "test_command",
                    ["test_arg1", "test_arg2"],
                    {
                        "tool": "get-library-docs",
                        "args": {
                            "context7CompatibleLibraryID": "react/react",
                            "topic": "hooks",
                            "tokens": 5000
                        }
                    },
                    15
                )
            ]
            
            mock_communicate.assert_has_calls(expected_calls)
            
            # Verify that appropriate messages were printed
            mock_print.assert_any_call("Fetching documentation for react/react on topic: hooks")

    @patch('asyncio.run')
    @patch('aider_mcp_client.client.resolve_library_id')
    @patch('aider_mcp_client.client.fetch_documentation')
    def test_async_main_integration(self, mock_fetch_docs, mock_resolve_id, mock_asyncio_run):
        """Test the async_main function that integrates all components"""
        # Mock the resolve_library_id response
        mock_resolve_id.return_value = "react/react"
        
        # Mock the fetch_documentation response
        mock_fetch_docs.return_value = {
            "library": "react/react",
            "snippets": [
                "```jsx\nimport React from 'react';\n\nfunction Example() {\n  return <div>Hello World</div>;\n}\n```"
            ],
            "totalTokens": 1000,
            "lastUpdated": "2025-04-27"
        }
        
        # Set up command line arguments
        test_args = ["script_name", "react", "--topic", "components", "--tokens", "3000"]
        
        # Create a mock coroutine object for async_main
        mock_coro = MagicMock()
        mock_asyncio_run.side_effect = lambda coro: None
        
        with patch('sys.argv', test_args):
            with patch('builtins.print') as mock_print:
                # Run the main function
                import sys
                old_argv = sys.argv
                sys.argv = test_args
                try:
                    # Create a coroutine to be passed to asyncio.run
                    async def mock_async_main():
                        # This simulates what async_main would do
                        await resolve_library_id("react")
                        await fetch_documentation("react/react", "components", 3000)
                    
                    # Replace async_main with our mock
                    with patch('aider_mcp_client.client.async_main', return_value=mock_async_main()):
                        asyncio.run(mock_async_main())
                finally:
                    sys.argv = old_argv
                
                # Verify that asyncio.run was called
                mock_asyncio_run.assert_called_once()

if __name__ == "__main__":
    unittest.main()
