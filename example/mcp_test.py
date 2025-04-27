import asyncio
import sys
import logging
from aider_mcp_client.mcp_sdk_client import resolve_library_id_sdk, fetch_documentation_sdk

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp_test")

async def test_context7_mcp():
    """Test Context7 MCP server using the aider_mcp_client library."""
    try:
        # Use the SDK client implementation from aider_mcp_client
        print("Connecting to Context7 MCP server...")
        
        # Resolve library ID for next.js
        library_name = "next.js"
        print(f"Resolving library ID for '{library_name}'...")
        library_id = await resolve_library_id_sdk(
            library_name=library_name,
            command="npx",
            args=["-y", "@upstash/context7-mcp@latest"],
            timeout=30
        )
        print(f"Resolved library ID: {library_id}")
        
        # Fetch documentation for the resolved library ID
        if library_id:
            print(f"Fetching documentation for '{library_id}'...")
            docs = await fetch_documentation_sdk(
                library_id=library_id,
                topic="routing",
                tokens=1000,
                command="npx",
                args=["-y", "@upstash/context7-mcp@latest"],
                timeout=30
            )
            if docs:
                print(f"Documentation received: {len(str(docs))} characters")
                if isinstance(docs, dict) and "content" in docs:
                    print(f"Documentation snippet: {docs['content'][:200]}...")
                else:
                    print(f"Documentation format: {type(docs)}")
            else:
                print("No documentation received")
        
    except Exception as e:
        logger.error(f"Error: {e}")
        print(f"Error: {e}", file=sys.stderr)

def main():
    asyncio.run(test_context7_mcp())

if __name__ == "__main__":
    main()
