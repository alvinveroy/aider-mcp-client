import subprocess
import json
import argparse
import sys
import time
import os
import asyncio
from pathlib import Path
import logging
from typing import Dict, Any, Optional, Tuple, List, Union
from aider_mcp_client import __version__

# Check for MCP SDK dependencies
try:
    from mcp import ClientSession, StdioServerParameters, types
    from mcp.client.stdio import stdio_client
    HAS_MCP_SDK = True
except ImportError:
    HAS_MCP_SDK = False
    logging.warning("MCP SDK not found. Some features will be limited. Install with: pip install mcp-sdk")

# Configure logging
logging.basicConfig(
    level=logging.WARNING,  # Default to WARNING to suppress INFO logs
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("mcp_client.log")]  # Log to file instead of console
)
logger = logging.getLogger("aider_mcp_client")

# Constants for MCP protocol
MCP_VERSION = "0.1.0"

def verbose():
    """Display version information and other details."""
    print(f"Aider MCP Client v{__version__}")
    print("A Python client for interacting with MCP (Model Control Protocol) servers")
    print("Default server: Context7 MCP")
    print("\nUsage: mcp_client <command> [args...]")
    print("For help: mcp_client --help")

def load_config():
    """
    Load MCP server configuration from config files in the following order:
    1. Current directory: ./.aider-mcp-client/config.json
    2. User home directory: ~/.aider-mcp-client/config.json
    3. Default configuration if no files found
    """
    default_config = {
        "mcpServers": {
            "context7": {
                "command": "npx",
                "args": ["-y", "@upstash/context7-mcp@latest"],
                "enabled": True,
                "timeout": 30
            }
        }
    }
    
    # Check current directory first
    local_config_path = Path.cwd() / ".aider-mcp-client" / "config.json"
    if local_config_path.exists():
        try:
            with open(local_config_path, 'r', encoding='utf-8') as f:
                logger.debug(f"Loading config from {local_config_path}")
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Error loading local config: {e}")
    
    # Then check user home directory
    home_config_path = Path.home() / ".aider-mcp-client" / "config.json"
    if home_config_path.exists():
        try:
            with open(home_config_path, 'r', encoding='utf-8') as f:
                logger.debug(f"Loading config from {home_config_path}")
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Error loading home config: {e}")
    
    logger.info("No config file found. Using default Context7 server configuration.")
    return default_config

async def communicate_with_mcp_server(command, args, request_data, timeout=30, debug_output=False):
    """Communicate with an MCP server via stdio using the MCP protocol."""
    # Check if we should use the MCP SDK
    config = load_config()
    use_sdk = False
    
    # Redirect stderr to a separate pipe to capture server messages
    import sys
    original_stderr = sys.stderr
    
    for server_name, server_config in config.get("mcpServers", {}).items():
        if (server_config.get("command") == command and 
            server_config.get("args") == args and 
            server_config.get("sdk", False)):
            use_sdk = True
            logger.debug(f"Using MCP SDK for server {server_name}")
            break
    
    if use_sdk:
        # Verify MCP SDK is available
        if not HAS_MCP_SDK:
            logger.error("MCP SDK is required but not installed. Install with: pip install mcp-sdk")
            return None
        return await communicate_with_mcp_sdk(command, args, request_data, timeout)
    
    try:
        # Start the MCP server process
        logger.debug(f"Starting MCP server process: {command} {' '.join(args)}")
        process = subprocess.Popen(
            [command] + args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8'
        )

        # Wait for server to initialize (check stderr for startup message)
        start_time = time.time()
        server_ready = False
        
        while time.time() - start_time < 5:  # Wait up to 5 seconds for server to start
            # Check if there's any stderr output indicating the server has started
            if process.stderr.readable():
                stderr_line = process.stderr.readline()
                if stderr_line:
                    if "MCP Server running on stdio" in stderr_line or "Documentation MCP Server running on stdio" in stderr_line:
                        logger.info(f"Server startup message detected: {stderr_line.strip()}")
                        server_ready = True
                        break
            await asyncio.sleep(0.1)
        
        if not server_ready:
            logger.warning("No server startup message detected, proceeding anyway")
        
        # Initialize MCP connection
        init_message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "clientName": "aider-mcp-client",
                "clientVersion": __version__,
                "capabilities": {
                    "prompts": {},
                    "resources": {},
                    "tools": {}
                }
            }
        }
        
        # Send initialization message
        init_json = json.dumps(init_message)
        logger.debug(f"Sending initialization: {init_json}")
        process.stdin.write(init_json + '\n')
        process.stdin.flush()
        
        # Wait for initialization response
        init_response = None
        start_time = time.time()
        while time.time() - start_time < 5 and not init_response:
            line = process.stdout.readline()
            if not line:
                break
                
            line = line.strip()
            if line:
                try:
                    response = json.loads(line)
                    if 'id' in response and response['id'] == 1:
                        init_response = response
                        logger.debug(f"Received initialization response: {line[:100]}...")
                        break
                except json.JSONDecodeError:
                    logger.debug(f"Received non-JSON line during init: {line}")
                    continue
            
            await asyncio.sleep(0.01)
            
        if not init_response:
            logger.error("Failed to initialize MCP connection")
            process.terminate()
            return None
            
        # Now send the actual request
        request_id = 2
        mcp_request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "callTool",
            "params": {
                "name": request_data.get("tool", "get-library-docs"),
                "arguments": request_data.get("args", {})
            }
        }
        
        request_json = json.dumps(mcp_request)
        logger.debug(f"Sending request: {request_json}")
        process.stdin.write(request_json + '\n')
        process.stdin.flush()

        # Read output with a timeout
        start_time = time.time()
        output = []
        buffer = ""
        
        # Use a simpler approach that works better with mocking in tests
        try:
            # Only use select/fcntl in non-test environments
            if 'unittest' not in sys.modules:
                import select
                import fcntl
                import os
                
                # Get the file descriptor
                fd = process.stdout.fileno()
                
                # Get the current flags
                fl = fcntl.fcntl(fd, fcntl.F_GETFL)
                
                # Set the non-blocking flag
                fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
                
                while time.time() - start_time < timeout:
                    # Use select to wait for data with a short timeout
                    ready_to_read, _, _ = select.select([process.stdout], [], [], 0.1)
                    
                    if process.stdout in ready_to_read:
                        chunk = process.stdout.read(4096)  # Read a chunk of data
                        if not chunk:  # End of file
                            break
                            
                        buffer += chunk
                        # Try to extract complete JSON objects from the buffer
                        while True:
                            try:
                                # Find the end of a JSON object
                                obj_end = buffer.find('\n')
                                if obj_end == -1:
                                    break  # No complete object yet
                                    
                                json_str = buffer[:obj_end].strip()
                                buffer = buffer[obj_end+1:]  # Remove processed part
                                
                                if json_str:  # Skip empty lines
                                    json_data = json.loads(json_str)
                                    output.append(json_data)
                                    logger.debug(f"Parsed JSON: {json_str[:100]}...")
                                    
                                    # Check for completion based on response structure
                                    if isinstance(json_data, dict) and ('library' in json_data or 'result' in json_data):
                                        logger.debug("Received complete response")
                                        # Don't break here, we need to collect the full response
                            except json.JSONDecodeError as e:
                                logger.debug(f"JSON decode error: {e} in: {json_str[:100]}...")
                                # Skip this line and continue with the next one
                                buffer = buffer[obj_end+1:]
                                continue
                    
                    # Check if process has terminated
                    if process.poll() is not None:
                        logger.debug("Process terminated")
                        # Process any remaining data
                        remaining = process.stdout.read()
                        if remaining:
                            buffer += remaining
                            # Try to parse any complete JSON objects
                            for line in buffer.splitlines():
                                try:
                                    if line.strip():
                                        json_data = json.loads(line.strip())
                                        output.append(json_data)
                                except json.JSONDecodeError:
                                    pass
                        break
            else:
                # Simpler approach for tests
                while time.time() - start_time < timeout:
                    line = process.stdout.readline()
                    if not line:  # End of file
                        break
                        
                    line = line.strip()
                    if line:  # Skip empty lines
                        try:
                            json_data = json.loads(line)
                            output.append(json_data)
                            # Check for completion based on response structure
                            if isinstance(json_data, dict) and ('library' in json_data or 'result' in json_data):
                                logger.debug("Received complete response")
                                # Don't break here, we need to collect the full response
                        except json.JSONDecodeError:
                            logger.debug(f"Received non-JSON line: {line}")
                            continue
                    
                    if process.poll() is not None:
                        logger.debug("Process terminated")
                        break
                    await asyncio.sleep(0.01)
        except Exception as e:
            logger.warning(f"Error in I/O handling: {e}. Falling back to simple readline.")
            # If the advanced I/O handling fails, fall back to simple readline
            while time.time() - start_time < timeout:
                line = process.stdout.readline()
                if not line:  # End of file
                    break
                    
                line = line.strip()
                if line:  # Skip empty lines
                    try:
                        json_data = json.loads(line)
                        output.append(json_data)
                        if isinstance(json_data, dict) and ('library' in json_data or 'result' in json_data):
                            break
                    except json.JSONDecodeError:
                        continue
                
                if process.poll() is not None:
                    break
                await asyncio.sleep(0.01)

        # Send shutdown message
        shutdown_message = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "shutdown"
        }
        process.stdin.write(json.dumps(shutdown_message) + '\n')
        process.stdin.flush()
        
        # Send exit notification
        exit_message = {
            "jsonrpc": "2.0",
            "method": "exit"
        }
        process.stdin.write(json.dumps(exit_message) + '\n')
        process.stdin.flush()
        process.stdin.close()  # Close stdin to signal we're done sending data

        # Terminate the process
        logger.debug("Terminating MCP server process")
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            logger.warning("Process did not terminate gracefully, killing")
            process.kill()

        # Check for any remaining errors in stderr
        stderr = process.stderr.read()
        if stderr:
            # Ignore the startup message which is not an error
            if "MCP Server running on stdio" in stderr or "Documentation MCP Server running on stdio" in stderr:
                logger.debug(f"Server startup message (already handled): {stderr.strip()}")
            else:
                logger.error(f"Server error: {stderr}")

        # Find the response for our request
        response = None
        
        # First try to find a response with the matching request ID
        for msg in output:
            if 'id' in msg and msg['id'] == request_id:
                response = msg
                break
        
        # If we didn't find a response with matching ID, look for any response with library data
        if not response:
            for msg in output:
                if isinstance(msg, dict):
                    # Check for library data in various formats
                    if 'library' in msg or 'snippets' in msg:
                        response = msg
                        break
                    elif 'result' in msg and isinstance(msg['result'], dict):
                        if 'library' in msg['result'] or 'snippets' in msg['result']:
                            response = msg
                            break
        
        # Debug output if requested
        if debug_output:
            print("\nDebug: MCP Server Response Analysis")
            print(f"Output messages: {len(output)}")
            for i, msg in enumerate(output):
                if isinstance(msg, dict):
                    keys = list(msg.keys())
                    print(f"Message {i}: {type(msg)} - Keys: {keys}")
                else:
                    print(f"Message {i}: {type(msg)} - {str(msg)[:100]}...")
                
        if response:
            # Extract the result from the MCP response
            if 'result' in response:
                # Format the result to match the expected structure
                if isinstance(response['result'], dict):
                    return response['result']
                else:
                    return {"result": response['result']}
            elif 'error' in response:
                logger.error(f"MCP server returned error: {response['error']}")
                return {"error": response['error']}
        
        logger.error("No valid response received")
        return None

    except Exception as e:
        logger.error(f"Error communicating with MCP server: {e}")
        return None

async def communicate_with_mcp_sdk(command, args, request_data, timeout=30):
    """
    Communicate with the MCP server using the MCP SDK.
    
    Args:
        command (str): The command to run.
        args (list): The arguments to pass to the command.
        request_data (dict): The data to send to the server.
        timeout (int): The timeout in seconds.
        
    Returns:
        dict: The response from the server.
    """
    if not HAS_MCP_SDK:
        logger.error("MCP SDK not installed. Cannot use SDK communication method.")
        logger.error("Install the MCP SDK with: pip install mcp-sdk")
        return None
        
    logger.debug(f"Communicating with MCP server using SDK: {command} {args}")
    logger.debug(f"Request data: {request_data}")
    
    try:
        # Create server parameters
        server_params = StdioServerParameters(
            command=command,
            args=args,
            env=None,
        )
        
        # Connect to the server
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                # Initialize the connection
                await session.initialize()
                
                # Determine which tool to call and with what arguments
                tool_name = request_data.get("tool")
                tool_args = request_data.get("args", {})
                
                # Call the tool
                result = await session.call_tool(tool_name, arguments=tool_args)
                logger.debug(f"SDK Response: {result}")
                
                return result
    except Exception as e:
        logger.error(f"Error communicating with MCP server using SDK: {e}")
        raise

async def resolve_library_id(library_name, custom_timeout=None, server_name="context7"):
    """Resolve a general library name to a Context7-compatible library ID."""
    config = load_config()
    # Get the server config from mcpServers
    server_config = config.get("mcpServers", {}).get(server_name, {})
    command = server_config.get("command", "npx")
    args = server_config.get("args", ["-y", "@upstash/context7-mcp@latest"])
    timeout = custom_timeout or server_config.get("timeout", 30)
    
    logger.info(f"Using timeout of {timeout} seconds for resolution with {server_name} server")
    
    # Use the SDK implementation if available
    if HAS_MCP_SDK:
        try:
            from aider_mcp_client.mcp_sdk_client import resolve_library_id_sdk
            logger.info(f"Using MCP SDK to resolve library ID for '{library_name}'")
            library_id = await resolve_library_id_sdk(
                library_name=library_name,
                command=command,
                args=args,
                timeout=timeout
            )
            
            # If we got a valid library ID, return it
            if library_id:
                return library_id
                
            # For common libraries, use known IDs as fallback
            if library_name.lower() == "react":
                logger.info("Using known library ID for React: facebook/react")
                return "facebook/react"
            elif library_name.lower() in ["next", "nextjs"]:
                logger.info("Using known library ID for Next.js: vercel/nextjs")
                return "vercel/nextjs"
                
            logger.info("Falling back to direct MCP communication")
        except Exception as e:
            logger.error(f"Error using SDK to resolve library ID: {str(e)}")
            logger.info("Falling back to direct MCP communication")
    
    # Construct MCP request for resolve-library-id tool (note the name change)
    request_data = {
        "tool": "resolve-library-id",  # Changed from resolve-library to resolve-library-id
        "args": {
            "libraryName": library_name
        }
    }
    
    try:
        # Communicate with the server
        response = await communicate_with_mcp_server(command, args, request_data, timeout)
        
        if not response:
            logger.error(f"No response received when resolving library ID for '{library_name}'")
            return None
        
        # Handle different response formats (SDK vs direct)
        if isinstance(response, str):
            # Direct string response
            return response
        elif isinstance(response, dict):
            if 'result' in response:
                return response.get('result')
            elif 'libraryId' in response:
                return response.get('libraryId')
            else:
                logger.error(f"Invalid response format when resolving library ID for '{library_name}'")
                logger.debug(f"Response: {response}")
                return None
        else:
            logger.error(f"Unexpected response type: {type(response)}")
            logger.debug(f"Response: {response}")
            return None
    
    except Exception as e:
        logger.error(f"Error resolving library ID for '{library_name}': {str(e)}")
        import traceback
        logger.debug(f"Traceback: {traceback.format_exc()}")
        return None

async def fetch_documentation(library_id, topic="", tokens=5000, custom_timeout=None, server_name="context7", display_output=True, output_buffer=None):
    """Fetch JSON documentation from an MCP server."""
    # Load server configuration
    config = load_config()
    # Get the server config from mcpServers
    server_config = config.get("mcpServers", {}).get(server_name, {})
    command = server_config.get("command", "npx")
    args = server_config.get("args", ["-y", "@upstash/context7-mcp@latest"])
    timeout = custom_timeout or server_config.get("timeout", 30)
    
    logger.info(f"Using timeout of {timeout} seconds with {server_name} server")
    
    # Check if we need to resolve the library ID first
    if '/' not in library_id:
        logger.info(f"Resolving library ID for '{library_id}'")
        try:
            resolved_id = await resolve_library_id(library_id, custom_timeout=timeout, server_name=server_name)
            if resolved_id:
                library_id = resolved_id
                logger.info(f"Resolved to '{library_id}'")
            else:
                # For common libraries, use known IDs as fallback
                if library_id.lower() == "react":
                    library_id = "facebook/react"
                    logger.info(f"Using known library ID for React: {library_id}")
                elif library_id.lower() in ["next", "nextjs"]:
                    library_id = "vercel/nextjs"
                    logger.info(f"Using known library ID for Next.js: {library_id}")
                else:
                    logger.warning(f"Could not resolve library ID. Using original: '{library_id}'")
        except Exception as e:
            logger.warning(f"Error resolving library ID: {str(e)}. Using original: '{library_id}'")

    # Use the SDK implementation if available
    if HAS_MCP_SDK:
        try:
            from aider_mcp_client.mcp_sdk_client import fetch_documentation_sdk
            logger.info(f"Using MCP SDK to fetch documentation for '{library_id}'")
            
            # Use a longer timeout for documentation fetching
            sdk_timeout = max(timeout, 60)  # At least 60 seconds for documentation
            
            result = await fetch_documentation_sdk(
                library_id=library_id,
                topic=topic,
                tokens=tokens,
                command=command,
                args=args,
                timeout=sdk_timeout
            )
            if result:
                return result
            logger.info("SDK returned no results. Falling back to direct MCP communication")
        except Exception as e:
            logger.error(f"Error using SDK to fetch documentation: {str(e)}")
            logger.info("Falling back to direct MCP communication")

    # Construct MCP request for get-library-docs tool
    request_data = {
        "tool": "get-library-docs",
        "args": {
            "context7CompatibleLibraryID": library_id,
            "topic": topic,
            "tokens": max(tokens, 5000)  # Ensure minimum of 5000 tokens
        }
    }
    
    # Log the request for debugging
    logger.debug(f"Sending request to MCP server: {json.dumps(request_data)}")
    
    # Use a longer timeout for documentation fetching
    doc_timeout = max(timeout, 60)  # At least 60 seconds for documentation

    # Communicate with the server
    logger.info(f"Fetching documentation for '{library_id}'{' on topic ' + topic if topic else ''}")
    
    try:
        # Set debug_output to True to help diagnose issues
        response = await communicate_with_mcp_server(command, args, request_data, doc_timeout, debug_output=True)
        
        # Print raw response for debugging
        logger.debug(f"Response from MCP server: {json.dumps(response) if response else 'None'}")
        
        if not response:
            logger.error("No valid response received from the server")
            return None

        logger.debug(f"Raw response type: {type(response)}")
        logger.debug(f"Raw response: {response}")

        # Handle different response formats (SDK vs direct)
        if isinstance(response, dict):
            if "library" not in response and "documentation" in response:
                # Format SDK response to match the expected format
                response = {
                    "library": library_id,
                    "snippets": response.get("documentation", []),
                    "totalTokens": response.get("tokenCount", tokens),
                    "lastUpdated": response.get("lastUpdated", "")
                }
            elif "result" in response and isinstance(response["result"], dict):
                # Handle nested result structure
                result = response["result"]
                response = {
                    "library": result.get("library", library_id),
                    "snippets": result.get("snippets", []),
                    "totalTokens": result.get("totalTokens", tokens),
                    "lastUpdated": result.get("lastUpdated", "")
                }

        # Format output for Aider compatibility
        aider_output = {
            "content": json.dumps(response, indent=2) if isinstance(response, dict) else str(response),
            "library": response.get("library", library_id) if isinstance(response, dict) else library_id,
            "snippets": response.get("snippets", []) if isinstance(response, dict) else [],
            "totalTokens": response.get("totalTokens", 0) if isinstance(response, dict) else 0,
            "lastUpdated": response.get("lastUpdated", "") if isinstance(response, dict) else ""
        }

        # If we have an output buffer, add the documentation to it
        # Otherwise display immediately
        if output_buffer is not None and isinstance(output_buffer, list):
            # Store the documentation in the buffer for later display
            if response and (isinstance(response, dict) and 
                            ('snippets' in response or 
                             ('result' in response and isinstance(response['result'], dict)))):
                output_buffer.append((response, library_id))
        elif display_output:
            # Display immediately
            display_documentation(response, library_id)
        
        # Save documentation to a JSON file
        output_file = f"{library_id.replace('/', '_')}_docs.json"
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(aider_output, f, indent=2, ensure_ascii=False)
            logger.info(f"Documentation saved to {output_file}")
        except Exception as e:
            logger.error(f"Error saving documentation to file: {str(e)}")
            
        return aider_output
    
    except Exception as e:
        logger.error(f"Error fetching documentation: {str(e)}")
        import traceback
        logger.debug(f"Traceback: {traceback.format_exc()}")
        return None

def list_supported_libraries():
    """List all libraries supported by Context7."""
    print("Fetching list of supported libraries from Context7...")
    print("This feature is not yet implemented. Please check https://context7.com for supported libraries.")
    return

def display_documentation(response, library_id):
    """Helper function to display documentation in the console."""
    if isinstance(response, dict) and "snippets" in response and response["snippets"]:
        # Print documentation header
        print(f"\n=== Documentation for {library_id} ===\n")
        
        for i, snippet in enumerate(response["snippets"]):
            # Print snippet header
            print(f"\n--- Snippet {i+1} ---")
            
            if isinstance(snippet, dict):
                if "title" in snippet:
                    print(f"Title: {snippet['title']}")
                
                if "content" in snippet:
                    print(f"\n{snippet['content']}\n")
            else:
                print(snippet)
        
        # Print token count
        print(f"\nTotal Tokens: {response.get('totalTokens', 0)}")
    else:
        # Create aider_output for JSON formatting
        aider_output = {
            "content": json.dumps(response, indent=2) if isinstance(response, dict) else str(response),
            "library": response.get("library", library_id) if isinstance(response, dict) else library_id,
            "snippets": response.get("snippets", []) if isinstance(response, dict) else [],
            "totalTokens": response.get("totalTokens", 0) if isinstance(response, dict) else 0,
            "lastUpdated": response.get("lastUpdated", "") if isinstance(response, dict) else ""
        }
        # Fallback to printing the full JSON if snippets not found
        formatted_output = json.dumps(aider_output, indent=2, ensure_ascii=False)
        print(formatted_output)

async def async_main():
    """Async entry point for the CLI."""
    # Set up command-line argument parsing
    parser = argparse.ArgumentParser(description="Aider MCP client for fetching library documentation.")
    
    # Global options that should be available for all commands
    parser.add_argument("-v", "--version", action="store_true", help="Show version information")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--verbose", action="store_true", help="Show detailed logs in console")
    parser.add_argument("--quiet", action="store_true", help="Suppress informational output")
    parser.add_argument("--server", default="context7", help="MCP server to use (default: context7)")
    parser.add_argument("--json", action="store_true", help="Force JSON output format")
    
    # Create subparsers for commands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Fetch command
    fetch_parser = subparsers.add_parser("fetch", help="Fetch JSON documentation for a library")
    fetch_parser.add_argument("library_id", help="Library ID or name (e.g., vercel/nextjs or just nextjs)")
    fetch_parser.add_argument("--topic", default="", help="Topic to filter documentation (optional)")
    fetch_parser.add_argument("--tokens", type=int, default=5000, help="Maximum tokens (default: 5000)")
    fetch_parser.add_argument("--timeout", type=int, default=None, help="Timeout in seconds (overrides config)")
    fetch_parser.add_argument("--server", default="context7", help="MCP server to use (default: context7)")
    fetch_parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    fetch_parser.add_argument("--verbose", action="store_true", help="Show detailed logs in console")
    fetch_parser.add_argument("--json", action="store_true", help="Force JSON output format")
    fetch_parser.add_argument("--output", help="Output file path (default: <library_id>_docs.json)")
    
    # Resolve command
    resolve_parser = subparsers.add_parser("resolve", help="Resolve a library name to a Context7-compatible ID")
    resolve_parser.add_argument("library_name", help="Library name to resolve (e.g., nextjs)")
    resolve_parser.add_argument("--timeout", type=int, default=None, help="Timeout in seconds (overrides config)")
    resolve_parser.add_argument("--server", default="context7", help="MCP server to use (default: context7)")
    resolve_parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    resolve_parser.add_argument("--verbose", action="store_true", help="Show detailed logs in console")
    resolve_parser.add_argument("--json", action="store_true", help="Force JSON output format")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List supported libraries")
    list_parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    list_parser.add_argument("--verbose", action="store_true", help="Show detailed logs in console")
    list_parser.add_argument("--json", action="store_true", help="Force JSON output format")
    
    args = parser.parse_args()

    # Set logging level based on command line arguments
    if hasattr(args, 'debug') and args.debug:
        logger.setLevel(logging.DEBUG)
    elif hasattr(args, 'verbose') and args.verbose:
        logger.setLevel(logging.INFO)
    elif hasattr(args, 'quiet') and args.quiet:
        logger.setLevel(logging.WARNING)
    else:
        # By default, use WARNING level to suppress info logs
        logger.setLevel(logging.WARNING)

    if args.version:
        verbose()
        return

    if not args.command:
        verbose()
        return

    try:
        # Get server name from command-specific argument if available, otherwise from global argument
        server_name = getattr(args, 'server', "context7")
        
        if args.command == "fetch":
            if hasattr(args, 'tokens') and args.tokens <= 0:
                logger.error("Error: Tokens must be a positive integer")
                return
            
            # Use command-line timeout if provided
            timeout = args.timeout if hasattr(args, 'timeout') and args.timeout else None
            
            # Load config to get default timeout if not specified
            if timeout is None:
                config = load_config()
                timeout = config.get("mcpServers", {}).get(server_name, {}).get("timeout", 30)
            
            # Get output file path if specified
            output_file = None
            if hasattr(args, 'output') and args.output:
                output_file = args.output
                
            # Create a buffer to store documentation if we're displaying it
            output_buffer = [] if not output_file else None
            
            result = await fetch_documentation(args.library_id, args.topic, args.tokens, 
                                     custom_timeout=timeout, server_name=server_name,
                                     display_output=False,  # Don't display immediately
                                     output_buffer=output_buffer)
            
            # If output file is specified, save to that file instead of default
            if output_file and result:
                try:
                    with open(output_file, "w", encoding="utf-8") as f:
                        json.dump(result, f, indent=2, ensure_ascii=False)
                    print(f"Documentation saved to {output_file}")
                except Exception as e:
                    logger.error(f"Error saving documentation to specified file: {str(e)}")
            
            # Now display any buffered documentation after MCP connection has ended
            if output_buffer is not None:
                if len(output_buffer) > 0:
                    for doc_data in output_buffer:
                        response, lib_id = doc_data
                        display_documentation(response, lib_id)
                else:
                    # If we have a result but nothing in the buffer, display the result directly
                    if result:
                        display_documentation(result, args.library_id)
                    else:
                        print("\nNo documentation was received from the server.")
        
        elif args.command == "resolve":
            # Use command-line timeout if provided
            timeout = args.timeout if hasattr(args, 'timeout') and args.timeout else None
            
            resolved = await resolve_library_id(args.library_name, custom_timeout=timeout, server_name=server_name)
            if resolved:
                if getattr(args, 'json', False):
                    # Output in JSON format
                    result = {
                        "libraryName": args.library_name,
                        "libraryId": resolved,
                        "status": "success"
                    }
                    print(json.dumps(result, indent=2, ensure_ascii=False))
                else:
                    print(f"Resolved '{args.library_name}' to: {resolved}")
            else:
                if getattr(args, 'json', False):
                    # Output in JSON format
                    result = {
                        "libraryName": args.library_name,
                        "status": "error",
                        "message": "Could not resolve library name"
                    }
                    print(json.dumps(result, indent=2, ensure_ascii=False))
                else:
                    print(f"Could not resolve library name: {args.library_name}")
        
        elif args.command == "list":
            if getattr(args, 'json', False):
                # Output in JSON format
                result = {
                    "status": "info",
                    "message": "This feature is not yet implemented. Please check https://context7.com for supported libraries."
                }
                print(json.dumps(result, indent=2, ensure_ascii=False))
            else:
                list_supported_libraries()
    
    except KeyboardInterrupt:
        logger.info("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        if hasattr(args, 'debug') and args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)

def main():
    """Entry point for the CLI."""
    asyncio.run(async_main())

if __name__ == "__main__":
    main()
