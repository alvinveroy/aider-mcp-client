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
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                # Initialize the connection
                await session.initialize()
                
                # Call the tool
                result = await session.call_tool(tool_name, arguments=tool_args)
                return result
    except Exception as e:
        logger.error(f"Failed to call MCP tool: {e}")
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
    
    result = await call_mcp_tool(
        command=command,
        args=args,
        tool_name="get-library-docs",
        tool_args=tool_args,
        timeout=timeout
    )
    
    if result:
        # Format output for Aider compatibility
        aider_output = {
            "content": json.dumps(result, indent=2),  # Aider expects a content field
            "library": result.get("library", ""),
            "snippets": result.get("snippets", []),
            "totalTokens": result.get("totalTokens", 0),
            "lastUpdated": result.get("lastUpdated", "")
        }
        return aider_output
    
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
    
    return result
