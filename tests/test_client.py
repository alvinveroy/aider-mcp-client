import unittest
import json
import os
import tempfile
from unittest.mock import patch, MagicMock
from pathlib import Path
from aider_mcp_client.client import (
    load_config, 
    communicate_with_mcp_server, 
    resolve_library_id, 
    fetch_documentation,
    list_supported_libraries
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
            self.assertEqual(config["mcp_server"]["command"], "npx")
            self.assertEqual(config["mcp_server"]["args"], ["-y", "@upstash/context7-mcp@latest"])
            self.assertEqual(config["mcp_server"]["tool"], "get-library-docs")
            self.assertEqual(config["mcp_server"]["timeout"], 30)
            self.assertEqual(config["mcp_server"]["enabled"], True)
    
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
    def test_communicate_with_mcp_server(self, mock_popen):
        """Test communication with MCP server"""
        # Mock the subprocess.Popen
        mock_process = MagicMock()
        mock_process.stdout.readline.return_value = '{"result": "test_result"}\n'
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process
        
        request_data = {"tool": "test-tool", "args": {"test_arg": "test_value"}}
        result = communicate_with_mcp_server("test_command", ["test_arg"], request_data, 5)
        
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
        
        result = resolve_library_id("library")
        
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
            result = fetch_documentation("library", "topic", 6000)
            
            # Check that resolve_library_id was called
            mock_resolve.assert_called_once_with("library")
            
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
            result = fetch_documentation("org/library", "topic", 6000)
            
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

if __name__ == "__main__":
    unittest.main()
