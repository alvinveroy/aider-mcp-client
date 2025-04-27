#!/bin/bash

# Test connection to Context7 MCP server
echo "Testing connection to Context7 MCP server..."

# Check if npx is installed
if ! command -v npx &> /dev/null; then
    echo "❌ Error: npx is not installed. Please install Node.js and npm."
    exit 1
fi

# Check if Python dependencies are installed
python -c "import mcp" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠️ Warning: MCP SDK not installed. Installing now..."
    pip install mcp-sdk
fi

# Run the test connection script
echo "Running test connection script..."
python aider_mcp_client/test_connection.py

# Check the exit code
if [ $? -eq 0 ]; then
    echo "✅ Connection test successful!"
else
    echo "❌ Connection test failed."
    echo "Please check your internet connection and make sure you have Node.js installed."
    echo "You may also need to install the Context7 MCP server with: npm install -g @upstash/context7-mcp"
fi
