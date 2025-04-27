import unittest
import json
from pathlib import Path
from mcp_client.client import load_config, fetch_documentation

class TestMcpClient(unittest.TestCase):
    def test_load_config_default(self):
        config = load_config()
        self.assertEqual(config["mcp_server"]["command"], "npx")
        self.assertEqual(config["mcp_server"]["args"], ["-y", "@upstash/context7-mcp@latest"])
        self.assertEqual(config["mcp_server"]["tool"], "fetch_documentation")

    def test_load_config_custom(self):
        # Create a temporary config file
        config_path = Path.home() / ".mcp_client" / "config.json"
        config_path.parent.mkdir(exist_ok=True)
        custom_config = {
            "mcp_server": {
                "command": "custom_command",
                "args": ["arg1", "arg2"],
                "tool": "custom_tool"
            }
        }
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(custom_config, f)
        
        config = load_config()
        self.assertEqual(config["mcp_server"]["command"], "custom_command")
        self.assertEqual(config["mcp_server"]["args"], ["arg1", "arg2"])
        self.assertEqual(config["mcp_server"]["tool"], "custom_tool")
        
        # Clean up
        config_path.unlink()

if __name__ == "__main__":
    unittest.main()