#!/usr/bin/env python3
"""
Test script to verify connection to Context7 MCP server.
This script attempts to connect to the server and resolve a library ID.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path to allow importing from aider_mcp_client
sys.path.insert(0, str(Path(__file__).parent.parent))

from aider_mcp_client.client import resolve_library_id, fetch_documentation
from aider_mcp_client.mcp_sdk_client import connect_to_mcp_server

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("test_connection")

async def test_connection():
    """Test connection to Context7 MCP server."""
    logger.info("Testing connection to Context7 MCP server...")
    
    # Test basic connection
    command = "npx"
    args = ["-y", "@upstash/context7-mcp@latest"]
    
    try:
        # First, try to connect using the SDK client
        logger.info("Testing connection using MCP SDK...")
        from aider_mcp_client.mcp_sdk_client import connect_to_mcp_server
        
        server_info = await connect_to_mcp_server(command, args, timeout=30)
        if server_info:
            logger.info(f"✅ Successfully connected to MCP server: {server_info.get('server_name', 'unknown')} v{server_info.get('server_version', 'unknown')}")
        else:
            logger.error("❌ Failed to connect to MCP server using SDK")
    
        # Test resolving a library ID
        logger.info("Testing library ID resolution...")
        library_name = "react"
        library_id = await resolve_library_id(library_name)
        
        if library_id:
            logger.info(f"✅ Successfully resolved library ID for '{library_name}': {library_id}")
        else:
            logger.error(f"❌ Failed to resolve library ID for '{library_name}'")
        
        # Test fetching documentation
        if library_id:
            logger.info(f"Testing documentation fetching for '{library_id}'...")
            docs = await fetch_documentation(library_id, topic="hooks", tokens=5000)
            
            if docs:
                logger.info(f"✅ Successfully fetched documentation for '{library_id}'")
                logger.info(f"   Total tokens: {docs.get('totalTokens', 'unknown')}")
                logger.info(f"   Number of snippets: {len(docs.get('snippets', []))}")
            else:
                logger.error(f"❌ Failed to fetch documentation for '{library_id}'")
        
        return True
    except Exception as e:
        logger.error(f"❌ Error testing connection: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = asyncio.run(test_connection())
    if success:
        logger.info("✅ All tests completed successfully")
        sys.exit(0)
    else:
        logger.error("❌ Some tests failed")
        sys.exit(1)
