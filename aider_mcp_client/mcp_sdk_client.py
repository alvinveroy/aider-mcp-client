"""
MCP SDK client implementation for aider-mcp-client.
This provides a more robust implementation using the official MCP Python SDK.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union

from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client

logger = logging.getLogger("aider_mcp_client.mcp_sdk_client")

async def connect_to_mcp_server(
    command: str,
    args: List[str],
    timeout: int = 30
) -> Optional[Dict[str, Any]]:
    """
    Connect to an MCP server using the MCP Python SDK.
    
    Args:
        command: The command to run the MCP server
        args: Arguments for the command
        timeout: Timeout in seconds
        
    Returns:
        Server capabilities or None if connection failed
    """
    server_params = StdioServerParameters(
        command=command,
        args=args,
        env=None,
    )
    
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                # Initialize the connection
                init_result = await session.initialize()
                logger.debug(f"Connected to MCP server: {init_result.server_info.name} v{init_result.server_info.version}")
                return {
                    "server_name": init_result.server_info.name,
                    "server_version": init_result.server_info.version,
                    "capabilities": init_result.capabilities
                }
    except Exception as e:
        logger.error(f"Failed to connect to MCP server: {e}")
        return None

async def call_mcp_tool(
    command: str,
    args: List[str],
    tool_name: str,
    tool_args: Dict[str, Any],
    timeout: int = 30
) -> Optional[Dict[str, Any]]:
    """
    Call a tool on an MCP server using the MCP Python SDK.
    
    Args:
        command: The command to run the MCP server
        args: Arguments for the command
        tool_name: Name of the tool to call
        tool_args: Arguments for the tool
        timeout: Timeout in seconds
        
    Returns:
        Tool result or None if call failed
    """
    server_params = StdioServerParameters(
        command=command,
        args=args,
        env=None,
    )
    
    try:
        # Create a timeout for the entire operation
        async with asyncio.timeout(timeout):
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    # Initialize the connection
                    await session.initialize()
                    
                    # Call the tool
                    logger.debug(f"Calling MCP tool: {tool_name} with args: {tool_args}")
                    result = await session.call_tool(tool_name, arguments=tool_args)
                    logger.debug(f"MCP tool result type: {type(result)}")
                    return result
    except asyncio.TimeoutError:
        logger.error(f"Timeout after {timeout}s when calling MCP tool: {tool_name}")
        return None
    except Exception as e:
        logger.error(f"Failed to call MCP tool {tool_name}: {e}")
        return None

async def fetch_documentation_sdk(
    library_id: str,
    topic: str = "",
    tokens: int = 5000,
    command: str = "npx",
    args: List[str] = ["-y", "@upstash/context7-mcp@latest"],
    timeout: int = 30
) -> Optional[Dict[str, Any]]:
    """
    Fetch documentation using the MCP Python SDK.
    
    Args:
        library_id: Library ID to fetch documentation for
        topic: Topic to filter documentation
        tokens: Maximum tokens to return
        command: Command to run the MCP server
        args: Arguments for the command
        timeout: Timeout in seconds
        
    Returns:
        Documentation or None if fetch failed
    """
    tool_args = {
        "context7CompatibleLibraryID": library_id,
        "topic": topic,
        "tokens": max(tokens, 5000)  # Ensure minimum of 5000 tokens
    }
    
    try:
        result = await call_mcp_tool(
            command=command,
            args=args,
            tool_name="get-library-docs",
            tool_args=tool_args,
            timeout=timeout
        )
        
        if not result:
            logger.warning(f"No documentation returned for library ID: {library_id}")
            return None
            
        # Format output for Aider compatibility
        if isinstance(result, dict):
            # Extract relevant fields from the result
            aider_output = {
                "content": result.get("content", json.dumps(result, indent=2)),
                "library": result.get("library", library_id),
                "snippets": result.get("snippets", []),
                "totalTokens": result.get("totalTokens", 0),
                "lastUpdated": result.get("lastUpdated", "")
            }
            return aider_output
        else:
            # Handle case where result is not a dictionary
            logger.warning(f"Unexpected result type: {type(result)}")
            return {"content": str(result), "library": library_id}
    except Exception as e:
        logger.error(f"Error fetching documentation: {e}")
        return None

async def resolve_library_id_sdk(
    library_name: str,
    command: str = "npx",
    args: List[str] = ["-y", "@upstash/context7-mcp@latest"],
    timeout: int = 30
) -> Optional[str]:
    """
    Resolve a library name to a Context7-compatible ID using the MCP Python SDK.
    
    Args:
        library_name: Library name to resolve
        command: Command to run the MCP server
        args: Arguments for the command
        timeout: Timeout in seconds
        
    Returns:
        Resolved library ID or None if resolution failed
    """
    tool_args = {
        "libraryName": library_name
    }
    
    result = await call_mcp_tool(
        command=command,
        args=args,
        tool_name="resolve-library-id",
        tool_args=tool_args,
        timeout=timeout
    )
    
    if result and isinstance(result, dict):
        return result.get("libraryId")
    elif result and isinstance(result, str):
        return result
    
    return None
