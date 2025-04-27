#!/usr/bin/env python3
"""
Script to fetch React.js documentation.
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

# Add parent directory to path to allow importing from aider_mcp_client
sys.path.insert(0, str(Path(__file__).parent.parent))

from aider_mcp_client.client import fetch_documentation

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("get_react_docs")

async def get_react_docs():
    """Fetch React.js documentation directly."""
    logger.info("Fetching React.js documentation...")
    
    # Use the library ID directly to avoid resolution step
    library_id = "facebook/react"
    topic = "hooks"  # Focus on React hooks
    
    docs = await fetch_documentation(library_id, topic=topic, tokens=10000)
    
    if docs:
        logger.info(f"✅ Successfully fetched documentation for React")
        logger.info(f"   Total tokens: {docs.get('totalTokens', 'unknown')}")
        logger.info(f"   Number of snippets: {len(docs.get('snippets', []))}")
        
        # Save to file for easier viewing
        with open("react_docs.json", "w") as f:
            json.dump(docs, f, indent=2)
        logger.info("✅ Saved documentation to react_docs.json")
        
        return True
    else:
        logger.error("❌ Failed to fetch React documentation")
        return False

if __name__ == "__main__":
    success = asyncio.run(get_react_docs())
    sys.exit(0 if success else 1)
