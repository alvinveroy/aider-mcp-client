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
) -> Optional[Any]:
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
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                # Initialize the connection
                await session.initialize()
                
                # List available tools to verify the tool exists
                tools = await session.list_tools()
                logger.debug(f"Available tools: {[tool.name for tool in tools.tools]}")
                
                # Verify the tool exists
                tool_exists = any(tool.name == tool_name for tool in tools.tools)
                if not tool_exists:
                    available_tools = [tool.name for tool in tools.tools]
                    logger.error(f"Tool '{tool_name}' not found. Available tools: {available_tools}")
                    if "resolve-library-id" in available_tools and tool_name == "resolve-library":
                        logger.info("Using 'resolve-library-id' instead of 'resolve-library'")
                        tool_name = "resolve-library-id"
                    elif "resolve-library" in available_tools and tool_name == "resolve-library-id":
                        logger.info("Using 'resolve-library' instead of 'resolve-library-id'")
                        tool_name = "resolve-library"
                
                # Call the tool with timeout
                logger.debug(f"Calling MCP tool: {tool_name} with args: {tool_args}")
                try:
                    # Use asyncio.wait_for instead of asyncio.timeout for better compatibility
                    result = await asyncio.wait_for(
                        session.call_tool(tool_name, arguments=tool_args),
                        timeout=timeout
                    )
                    logger.debug(f"MCP tool result type: {type(result)}")
                    
                    # Handle CallToolResult type
                    if hasattr(result, 'result'):
                        logger.debug(f"Result has 'result' attribute: {result.result}")
                        
                        # For Context7, directly extract the content if it's a documentation request
                        if tool_name == "get-library-docs" and hasattr(result, 'content'):
                            logger.debug(f"Direct content extraction for get-library-docs")
                            # This is a special case for Context7 documentation
                            return result
                        
                        # For library resolution, try to extract libraryId
                        if tool_name == "resolve-library-id" and hasattr(result, 'libraryId'):
                            logger.debug(f"Direct libraryId extraction: {result.libraryId}")
                            return result
                        
                        # If we can't extract directly, return the whole result
                        return result
                    return result
                except asyncio.TimeoutError:
                    logger.error(f"Timeout after {timeout}s when calling MCP tool: {tool_name}")
                    return None
                except Exception as e:
                    logger.error(f"Error calling tool {tool_name}: {e}")
                    if "400" in str(e):
                        logger.error(f"Bad request (400) when calling {tool_name}. Check your arguments: {tool_args}")
                    return None
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
    # Normalize library ID - remove .js extension if present
    if library_id.endswith('.js'):
        library_id = library_id[:-3]
        logger.info(f"Normalized library ID to: {library_id}")
    
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
            
        # Handle CallToolResult type from MCP SDK
        if hasattr(result, 'result'):
            # Debug the full result object to understand its structure
            logger.debug(f"CallToolResult attributes: {dir(result)}")
            
            # Extract the actual result data from CallToolResult
            result_data = result.result
            logger.debug(f"Extracted result from CallToolResult: {type(result_data)}")
            
            # For Context7, the documentation is in the result data
            if isinstance(result_data, dict) and "content" in result_data:
                logger.debug(f"Found content in result dictionary")
                documentation = result_data["content"]
                return {
                    "content": documentation if isinstance(documentation, str) else json.dumps(documentation, indent=2),
                    "library": library_id,
                    "snippets": result_data.get('snippets', []),
                    "totalTokens": result_data.get('totalTokens', tokens),
                    "lastUpdated": result_data.get('lastUpdated', "")
                }
            
            # If result_data has content attribute, use that
            if hasattr(result_data, 'content'):
                logger.debug(f"Found content attribute in result data")
                documentation = result_data.content
                return {
                    "content": documentation if isinstance(documentation, str) else json.dumps(documentation, indent=2),
                    "library": library_id,
                    "snippets": getattr(result_data, 'snippets', []),
                    "totalTokens": getattr(result_data, 'totalTokens', tokens),
                    "lastUpdated": getattr(result_data, 'lastUpdated', "")
                }
            
            # Try to access the result data as a dictionary using __dict__
            if hasattr(result_data, '__dict__'):
                result_data_dict = result_data.__dict__
                logger.debug(f"Result data __dict__: {result_data_dict}")
                if 'content' in result_data_dict:
                    documentation = result_data_dict['content']
                    return {
                        "content": documentation if isinstance(documentation, str) else json.dumps(documentation, indent=2),
                        "library": library_id,
                        "snippets": result_data_dict.get('snippets', []),
                        "totalTokens": result_data_dict.get('totalTokens', tokens),
                        "lastUpdated": result_data_dict.get('lastUpdated', "")
                    }
            
            # If result_data is a dictionary, use it directly
            if isinstance(result_data, dict):
                result = result_data
            # Handle text content array from Context7
            elif hasattr(result_data, 'content'):
                content = result_data.content
                logger.debug(f"Found content in result_data: {type(content)}")
                
                if isinstance(content, list):
                    # Extract text from TextContent objects
                    text_content = []
                    for item in content:
                        if hasattr(item, 'text'):
                            text_content.append(item.text)
                        elif isinstance(item, dict) and 'text' in item:
                            text_content.append(item['text'])
                        elif hasattr(item, '__dict__'):
                            item_dict = item.__dict__
                            if 'text' in item_dict:
                                text_content.append(item_dict['text'])
                    
                    documentation = "\n".join(text_content)
                    logger.debug(f"Extracted text content: {len(documentation)} characters")
                    return {
                        "content": documentation,
                        "library": library_id,
                        "snippets": [],
                        "totalTokens": tokens,
                        "lastUpdated": ""
                    }
                elif isinstance(content, str):
                    return {
                        "content": content,
                        "library": library_id,
                        "snippets": [],
                        "totalTokens": tokens,
                        "lastUpdated": ""
                    }
            # Try to parse as JSON if it's a string
            elif isinstance(result_data, str):
                try:
                    result = json.loads(result_data)
                except json.JSONDecodeError:
                    # If it's not JSON, use as raw documentation
                    return {
                        "content": result_data,
                        "library": library_id,
                        "snippets": [],
                        "totalTokens": tokens,
                        "lastUpdated": ""
                    }
            else:
                # For other types, convert to string representation
                # Check if it has a content attribute (common in Context7 responses)
                if hasattr(result_data, 'content'):
                    content = result_data.content
                    if isinstance(content, list):
                        # Extract text from TextContent objects
                        text_content = []
                        for item in content:
                            if hasattr(item, 'text'):
                                text_content.append(item.text)
                        documentation = "\n".join(text_content)
                    else:
                        documentation = str(content)
                    
                    return {
                        "content": documentation,
                        "library": library_id,
                        "snippets": [],
                        "totalTokens": tokens,
                        "lastUpdated": ""
                    }
                else:
                    # Last resort: convert the whole object to string
                    return {
                        "content": str(result_data),
                        "library": library_id,
                        "snippets": [],
                        "totalTokens": tokens,
                        "lastUpdated": ""
                    }
        
        # Format output for Aider compatibility
        if isinstance(result, dict):
            # Extract relevant fields from the result
            documentation = result.get("documentation", "")
            if not documentation and "content" in result:
                documentation = result.get("content", "")
            
            aider_output = {
                "content": documentation if isinstance(documentation, str) else json.dumps(documentation, indent=2),
                "library": result.get("library", library_id),
                "snippets": result.get("snippets", []),
                "totalTokens": result.get("totalTokens", tokens),
                "lastUpdated": result.get("lastUpdated", "")
            }
            return aider_output
        else:
            # Handle case where result is not a dictionary
            logger.debug(f"Processing non-dictionary result type: {type(result)}")
            
            # If it's a CallToolResult, extract the result field
            if hasattr(result, 'result'):
                result_data = result.result
                logger.debug(f"Extracted result data type: {type(result_data)}")
                
                # If result_data is a dictionary with content
                if isinstance(result_data, dict) and "content" in result_data:
                    documentation = result_data["content"]
                    return {
                        "content": documentation if isinstance(documentation, str) else json.dumps(documentation, indent=2),
                        "library": library_id,
                        "snippets": result_data.get('snippets', []),
                        "totalTokens": result_data.get('totalTokens', tokens),
                        "lastUpdated": result_data.get('lastUpdated', "")
                    }
                
                # If result_data has content attribute
                if hasattr(result_data, 'content'):
                    content = result_data.content
                    if isinstance(content, list):
                        # Extract text from TextContent objects
                        text_content = []
                        for item in content:
                            if hasattr(item, 'text'):
                                text_content.append(item.text)
                        documentation = "\n".join(text_content)
                    else:
                        documentation = str(content)
                    
                    return {
                        "content": documentation,
                        "library": library_id,
                        "snippets": getattr(result_data, 'snippets', []),
                        "totalTokens": getattr(result_data, 'totalTokens', tokens),
                        "lastUpdated": getattr(result_data, 'lastUpdated', "")
                    }
            
            # Try to extract content directly from result
            if hasattr(result, 'content'):
                content = result.content
                if isinstance(content, list):
                    # Extract text from TextContent objects
                    text_content = []
                    for item in content:
                        if hasattr(item, 'text'):
                            text_content.append(item.text)
                    documentation = "\n".join(text_content)
                else:
                    documentation = str(content)
                
                return {
                    "content": documentation,
                    "library": library_id,
                    "snippets": getattr(result, 'snippets', []),
                    "totalTokens": getattr(result, 'totalTokens', tokens),
                    "lastUpdated": getattr(result, 'lastUpdated', "")
                }
            
            # Last resort: convert to string
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
    # Normalize library name - remove .js extension if present
    if library_name.endswith('.js'):
        normalized_name = library_name[:-3]
        logger.info(f"Normalized library name from '{library_name}' to '{normalized_name}'")
        library_name = normalized_name
    
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
    
    if not result:
        return None
    
    # Handle CallToolResult type from MCP SDK
    if hasattr(result, 'result'):
        # Debug the full result object to understand its structure
        logger.debug(f"CallToolResult attributes: {dir(result)}")
                
        # For Context7, directly access the result field which contains the actual data
        result_data = result.result
        logger.debug(f"Extracted result from CallToolResult: {type(result_data)}")
                
        # Check if result_data is a dictionary with libraryId
        if isinstance(result_data, dict) and "libraryId" in result_data:
            logger.debug(f"Found libraryId in result dictionary: {result_data['libraryId']}")
            return result_data["libraryId"]
                
        # If result_data has a libraryId attribute, use that
        if hasattr(result_data, 'libraryId'):
            library_id = result_data.libraryId
            logger.debug(f"Found libraryId attribute in result: {library_id}")
            return library_id
                
        # Try to access the result as a dictionary using __dict__
        if hasattr(result_data, '__dict__'):
            result_dict = result_data.__dict__
            logger.debug(f"Result data __dict__: {result_dict}")
            if 'libraryId' in result_dict:
                return result_dict['libraryId']
        
        # If it's a dictionary, look for libraryId
        if isinstance(result_data, dict):
            if "libraryId" in result_data:
                return result_data.get("libraryId")
            # Sometimes the result might be nested
            for key, value in result_data.items():
                if isinstance(value, dict) and "libraryId" in value:
                    return value.get("libraryId")
        
        # If it's a string, try to parse as JSON
        elif isinstance(result_data, str):
            try:
                json_result = json.loads(result_data)
                if isinstance(json_result, dict):
                    return json_result.get("libraryId")
            except json.JSONDecodeError:
                # If it's not JSON, check if it looks like a library ID (contains a slash)
                if "/" in result_data:
                    return result_data
                
        # For Context7, we know some common library IDs
        if library_name.lower() == "react":
            logger.info("Using known library ID for React: facebook/react")
            return "facebook/react"
        elif library_name.lower() == "next" or library_name.lower() == "nextjs":
            logger.info("Using known library ID for Next.js: vercel/nextjs")
            return "vercel/nextjs"
                
    # Handle regular dictionary or string responses
    elif isinstance(result, dict):
        return result.get("libraryId")
    elif isinstance(result, str):
        return result
    
    logger.warning(f"Could not extract library ID from result type: {type(result)}")
    # Return hardcoded values for common libraries as fallback
    if library_name.lower() == "react":
        logger.info("Falling back to known library ID for React: facebook/react")
        return "facebook/react"
    elif library_name.lower() == "next" or library_name.lower() == "nextjs":
        logger.info("Falling back to known library ID for Next.js: vercel/nextjs")
        return "vercel/nextjs"
    
    return None
