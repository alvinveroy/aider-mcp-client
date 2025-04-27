import asyncio
import sys
import logging
from aider_mcp_client.mcp_sdk_client import resolve_library_id_sdk, fetch_documentation_sdk

# Set up logging
logging.basicConfig(level=logging.DEBUG)  # Set to DEBUG for more detailed logs
logger = logging.getLogger("mcp_test")

async def test_context7_mcp():
    """Test Context7 MCP server using the aider_mcp_client library."""
    try:
        # Use the SDK client implementation from aider_mcp_client
        print("Connecting to Context7 MCP server...")
        
        # Resolve library ID for react (not react.js)
        library_name = "react"  # Changed from next.js to react
        print(f"Resolving library ID for '{library_name}'...")
        library_id = await resolve_library_id_sdk(
            library_name=library_name,
            command="npx",
            args=["-y", "@upstash/context7-mcp@latest"],
            timeout=30
        )
        print(f"Resolved library ID: {library_id}")
        
        # If we couldn't resolve the ID, use a known working ID
        if not library_id:
            library_id = "facebook/react"
            print(f"Using hardcoded library ID: {library_id}")
        
        # Fetch documentation for the resolved library ID
        print(f"Fetching documentation for '{library_id}'...")
        docs = await fetch_documentation_sdk(
            library_id=library_id,
            topic="hooks",  # Changed from routing to hooks
            tokens=1000,
            command="npx",
            args=["-y", "@upstash/context7-mcp@latest"],
            timeout=30
        )
        
        if docs:
            print(f"Documentation received: {len(str(docs))} characters")
            if isinstance(docs, dict) and "content" in docs:
                content = docs["content"]
                print(f"Documentation content type: {type(content)}")
                if isinstance(content, str) and len(content) > 0:
                    print(f"Documentation snippet: {content[:200]}...")
                else:
                    print(f"Documentation content: {content}")
            else:
                print(f"Documentation format: {type(docs)}")
                print(f"Documentation keys: {docs.keys() if isinstance(docs, dict) else 'N/A'}")
                
            # Save documentation to a file for inspection
            with open("docs_output.txt", "w") as f:
                if isinstance(docs, dict) and "content" in docs:
                    f.write(str(docs["content"]))
                else:
                    f.write(str(docs))
            print("Documentation saved to docs_output.txt")
        else:
            print("No documentation received")
        
    except Exception as e:
        logger.error(f"Error: {e}")
        print(f"Error: {e}", file=sys.stderr)

def main():
    asyncio.run(test_context7_mcp())

if __name__ == "__main__":
    main()
