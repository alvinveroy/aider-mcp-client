import asyncio
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def test_context7_mcp():
    """Connect to Context7 MCP server via stdio and test resolve-library-id tool."""
    # Define server parameters
    server_params = StdioServerParameters(
        command="npx",  # Use "npx" if Bun is not installed
        args=["@upstash/context7-mcp@latest"],
        env=None
    )

    try:
        # Connect to server
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                # Initialize connection
                await session.initialize()
                print("Connected to Context7 MCP server")

                # List available tools
                tools = await session.list_tools()
                print("Available tools:", tools)

                # Call resolve-library-id tool
                result = await session.call_tool(
                    "resolve-library-id",
                    arguments={"library": "next.js"}
                )
                print("Resolve result:", result)

    except FileNotFoundError:
        print("Error: 'bunx' not found. Install Bun or use 'npx'.", file=sys.stderr)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)

def main():
    asyncio.run(test_context7_mcp())

if __name__ == "__main__":
    main()