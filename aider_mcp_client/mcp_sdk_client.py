"""
MCP SDK client implementation for aider-mcp-client.
This provides a more robust implementation using the official MCP Python SDK.
"""

import asyncio
import json
import logging
import subprocess
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
                # Handle different versions of MCP SDK
                if hasattr(init_result, 'server_info'):
                    server_name = init_result.server_info.name
                    server_version = init_result.server_info.version
                    logger.debug(f"Connected to MCP server: {server_name} v{server_version}")
                else:
                    # Newer versions might have different structure
                    server_name = getattr(init_result, 'name', 'Unknown')
                    server_version = getattr(init_result, 'version', 'Unknown')
                    logger.debug(f"Connected to MCP server: {server_name} v{server_version}")
                
                return {
                    "server_name": server_name,
                    "server_version": server_version,
                    "capabilities": getattr(init_result, 'capabilities', {})
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
    import subprocess
    
    # Start the MCP server process directly
    process = None
    try:
        # Start the process
        process = subprocess.Popen(
            [command] + args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8'
        )
        
        # Check if the process started successfully
        if process.poll() is not None:
            stderr = process.stderr.read() if process.stderr else "Unknown error"
            logger.error(f"Failed to start MCP server process: {stderr}")
            return None
            
        logger.debug(f"MCP server process started with PID: {process.pid}")
        
        # Create server parameters
        server_params = StdioServerParameters(
            command=command,
            args=args,
            env=None,
        )
        
        # Use a try-except block for each async operation to catch specific errors
        try:
            # Connect to the server
            async with stdio_client(server_params) as (read, write):
                try:
                    # Create session
                    async with ClientSession(read, write) as session:
                        try:
                            # Initialize with timeout
                            init_result = await asyncio.wait_for(
                                session.initialize(),
                                timeout=10  # Short timeout for initialization
                            )
                            # Handle different versions of MCP SDK
                            if hasattr(init_result, 'server_info'):
                                logger.debug(f"Connected to MCP server: {init_result.server_info.name} v{init_result.server_info.version}")
                            else:
                                # Newer versions might have different structure
                                server_name = getattr(init_result, 'name', 'Unknown')
                                server_version = getattr(init_result, 'version', 'Unknown')
                                logger.debug(f"Connected to MCP server: {server_name} v{server_version}")
                            
                            try:
                                # List tools with timeout
                                tools = await asyncio.wait_for(
                                    session.list_tools(),
                                    timeout=10  # Short timeout for listing tools
                                )
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
                                    elif not any(t for t in available_tools if "docs" in t.lower() or "library" in t.lower()):
                                        logger.error(f"No suitable tools found for documentation or library resolution")
                                        return None
                                
                                # Call the tool with timeout
                                logger.debug(f"Calling MCP tool: {tool_name} with args: {tool_args}")
                                try:
                                    # Use asyncio.wait_for with explicit timeout
                                    result = await asyncio.wait_for(
                                        session.call_tool(tool_name, arguments=tool_args),
                                        timeout=timeout
                                    )
                                    logger.debug(f"MCP tool result type: {type(result)}")
                                    
                                    # Debug the result structure
                                    if hasattr(result, 'result'):
                                        logger.debug(f"Result has 'result' attribute of type: {type(result.result)}")
                                        if hasattr(result.result, '__dict__'):
                                            logger.debug(f"Result.result.__dict__: {result.result.__dict__}")
                                    
                                    # For CallToolResult, extract the actual data
                                    if isinstance(result, types.CallToolResult):
                                        # For library resolution, extract the library ID
                                        if tool_name == "resolve-library-id":
                                            # Try to extract libraryId from the result
                                            if isinstance(result.result, dict) and "libraryId" in result.result:
                                                logger.debug(f"Found libraryId in result dictionary: {result.result['libraryId']}")
                                                return result.result["libraryId"]
                                            # If result.result is a string and looks like a library ID, return it
                                            elif isinstance(result.result, str) and "/" in result.result:
                                                logger.debug(f"Result appears to be a library ID: {result.result}")
                                                return result.result
                                        
                                        # For documentation fetching, handle the result
                                        elif tool_name == "get-library-docs":
                                            logger.debug(f"Processing get-library-docs result")
                                            # Return the result directly for further processing
                                            return result
                                    
                                    # Return the result as is
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
                                logger.error("Timeout when listing tools")
                                return None
                            except Exception as e:
                                logger.error(f"Error listing tools: {e}")
                                return None
                        except asyncio.TimeoutError:
                            logger.error("Timeout during initialization")
                            return None
                        except Exception as e:
                            logger.error(f"Error initializing session: {e}")
                            return None
                except Exception as e:
                    logger.error(f"Error creating session: {e}")
                    return None
        except Exception as e:
            logger.error(f"Error connecting to MCP server: {e}")
            return None
    except Exception as e:
        logger.error(f"Failed to set up MCP tool call: {e}")
        return None
    finally:
        # Ensure the process is terminated
        if process and process.poll() is None:
            try:
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
            except Exception as e:
                logger.error(f"Error terminating process: {e}")

async def fetch_documentation_sdk(
    library_id: str,
    topic: str = "",
    tokens: int = 5000,
    command: str = "npx",
    args: List[str] = ["-y", "@upstash/context7-mcp@latest"],
    timeout: int = 60  # Increased timeout for documentation fetching
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
        # First check if the server is responsive
        logger.debug(f"Checking connection to MCP server before fetching documentation")
        server_params = StdioServerParameters(
            command=command,
            args=args,
            env=None,
        )
        
        # Try to connect and initialize first
        try:
            # Use a direct approach without TaskGroup to avoid unhandled exceptions
            process = subprocess.Popen(
                [command] + args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8'
            )
            
            # Check if the process started successfully
            if process.poll() is not None:
                logger.error(f"Failed to start MCP server process: {process.stderr.read()}")
                return None
                
            logger.debug(f"MCP server process started with PID: {process.pid}")
            
            # Now use the SDK to connect to the running process
            try:
                async with stdio_client(server_params) as (read, write):
                    async with ClientSession(read, write) as session:
                        # Initialize the connection with timeout
                        try:
                            init_result = await asyncio.wait_for(
                                session.initialize(),
                                timeout=10  # Short timeout for initialization
                            )
                            # Handle different versions of MCP SDK
                            if hasattr(init_result, 'server_info'):
                                logger.debug(f"Connected to MCP server: {init_result.server_info.name} v{init_result.server_info.version}")
                            else:
                                # Newer versions might have different structure
                                server_name = getattr(init_result, 'name', 'Unknown')
                                server_version = getattr(init_result, 'version', 'Unknown')
                                logger.debug(f"Connected to MCP server: {server_name} v{server_version}")
                            
                            # List available tools to verify the tool exists
                            tools = await asyncio.wait_for(
                                session.list_tools(),
                                timeout=10  # Short timeout for listing tools
                            )
                            available_tools = [tool.name for tool in tools.tools]
                            logger.debug(f"Available tools: {available_tools}")
                            
                            # Check if get-library-docs is available
                            if "get-library-docs" not in available_tools:
                                logger.error(f"Tool 'get-library-docs' not found. Available tools: {available_tools}")
                                # Try alternative tool names
                                alt_tool_name = None
                                for tool_name in available_tools:
                                    if "docs" in tool_name.lower() or "documentation" in tool_name.lower():
                                        alt_tool_name = tool_name
                                        logger.info(f"Found alternative documentation tool: {alt_tool_name}")
                                        break
                                
                                if alt_tool_name:
                                    logger.info(f"Using alternative tool: {alt_tool_name}")
                                    # Call the tool directly without using call_mcp_tool
                                    try:
                                        result = await asyncio.wait_for(
                                            session.call_tool(alt_tool_name, arguments=tool_args),
                                            timeout=timeout
                                        )
                                        logger.debug(f"Tool result type: {type(result)}")
                                    except Exception as tool_error:
                                        logger.error(f"Error calling tool {alt_tool_name}: {tool_error}")
                                        return None
                                else:
                                    logger.error("No suitable documentation tool found")
                                    return None
                            else:
                                # Call the tool directly without using call_mcp_tool
                                try:
                                    result = await asyncio.wait_for(
                                        session.call_tool("get-library-docs", arguments=tool_args),
                                        timeout=timeout
                                    )
                                    logger.debug(f"Tool result type: {type(result)}")
                                except Exception as tool_error:
                                    logger.error(f"Error calling get-library-docs: {tool_error}")
                                    return None
                        except asyncio.TimeoutError:
                            logger.error(f"Timeout during MCP server initialization or tool listing")
                            return None
                        except Exception as init_error:
                            logger.error(f"Error during MCP server initialization: {init_error}")
                            return None
            except Exception as sdk_error:
                logger.error(f"Error using MCP SDK: {sdk_error}")
                return None
            finally:
                # Ensure the process is terminated
                if process and process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        process.kill()
        except Exception as conn_error:
            logger.error(f"Error connecting to MCP server: {conn_error}")
            return None
        
        if not result:
            logger.warning(f"No documentation returned for library ID: {library_id}")
            # Try direct MCP communication as fallback
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
    
    # For common libraries, use known IDs directly
    if library_name.lower() == "react":
        logger.info("Using known library ID for React: facebook/react")
        return "facebook/react"
    elif library_name.lower() in ["next", "nextjs"]:
        logger.info("Using known library ID for Next.js: vercel/nextjs")
        return "vercel/nextjs"
    
    tool_args = {
        "libraryName": library_name
    }
    
    try:
        result = await call_mcp_tool(
            command=command,
            args=args,
            tool_name="resolve-library-id",
            tool_args=tool_args,
            timeout=timeout
        )
        
        if not result:
            logger.warning(f"No result returned when resolving library ID for '{library_name}'")
            return None
        
        # If result is a string, check if it looks like a library ID
        if isinstance(result, str):
            if "/" in result:
                logger.debug(f"Result is a library ID string: {result}")
                return result
            else:
                logger.debug(f"Result is a string but not a library ID: {result}")
        
        # If result is a dictionary, look for libraryId
        if isinstance(result, dict):
            if "libraryId" in result:
                logger.debug(f"Found libraryId in result dictionary: {result['libraryId']}")
                return result["libraryId"]
        
        # Handle CallToolResult type from MCP SDK
        if isinstance(result, types.CallToolResult):
            logger.debug(f"Processing CallToolResult: {result}")
            
            # Extract the result field
            result_data = result.result
            logger.debug(f"Extracted result data type: {type(result_data)}")
            
            # If result_data is a string and looks like a library ID
            if isinstance(result_data, str) and "/" in result_data:
                logger.debug(f"Result data is a library ID string: {result_data}")
                return result_data
            
            # If result_data is a dictionary with libraryId
            if isinstance(result_data, dict) and "libraryId" in result_data:
                logger.debug(f"Found libraryId in result data: {result_data['libraryId']}")
                return result_data["libraryId"]
            
            # Try to access attributes directly
            if hasattr(result_data, 'libraryId'):
                library_id = result_data.libraryId
                logger.debug(f"Found libraryId attribute: {library_id}")
                return library_id
            
            # Try to access as dictionary using __dict__
            if hasattr(result_data, '__dict__'):
                result_dict = result_data.__dict__
                logger.debug(f"Result data __dict__: {result_dict}")
                if 'libraryId' in result_dict:
                    return result_dict['libraryId']
        
        logger.warning(f"Could not extract library ID from result type: {type(result)}")
        return None
        
    except Exception as e:
        logger.error(f"Error resolving library ID: {e}")
        return None
