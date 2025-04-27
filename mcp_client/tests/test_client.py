import unittest
import os
import json
import tempfile
from mcp_client.client import load_config

class TestClientConfig(unittest.TestCase):
    def test_load_default_config(self):
        """Test that default config is loaded when no path is given"""
        config = load_config()
        self.assertEqual(config["server"], "Context7")
        self.assertEqual(config["host"], "localhost")
        self.assertEqual(config["port"], 8000)
        self.assertEqual(config["timeout"], 30)

    def test_load_custom_config(self):
        """Test that custom config overrides defaults"""
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as f:
            custom_config = {
                "server": "TestServer",
                "port": 9000
            }
            json.dump(custom_config, f)
            f.close()
            
            config = load_config(f.name)
            os.unlink(f.name)
            
            # Check overridden values
            self.assertEqual(config["server"], "TestServer")
            self.assertEqual(config["port"], 9000)
            # Check defaults for non-overridden values
            self.assertEqual(config["host"], "localhost")
            self.assertEqual(config["timeout"], 30)

    def test_placeholder(self):
        """Placeholder for future tests"""
        self.assertTrue(True)

if __name__ == "__main__":
    unittest.main()
