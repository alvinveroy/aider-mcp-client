import subprocess
import json
import argparse
import sys
import time
import os
from pathlib import Path
import logging
from aider_mcp_client import __version__

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("aider_mcp_client")

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
        "mcp_server": {
            "command": "npx",
            "args": ["-y", "@upstash/context7-mcp@latest"],
            "tool": "get-library-docs",
            "timeout": 30,
            "enabled": True
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

def communicate_with_mcp_server(command, args, request_data, timeout=30):
    """Communicate with an MCP server via stdio."""
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

        # Send JSON request to the server's stdin
        request_json = json.dumps(request_data)
        logger.debug(f"Sending request: {request_json}")
        process.stdin.write(request_json + '\n')
        process.stdin.flush()

        # Read output with a timeout
        start_time = time.time()
        output = []
        while time.time() - start_time < timeout:
            line = process.stdout.readline()
            if line:
                try:
                    json_data = json.loads(line.strip())
                    output.append(json_data)
                    # Check for completion based on response structure
                    if isinstance(json_data, dict) and ('library' in json_data or 'result' in json_data):
                        logger.debug("Received complete response")
                        break
                except json.JSONDecodeError:
                    logger.debug(f"Received non-JSON line: {line.strip()}")
                    continue
            if process.poll() is not None:
                logger.debug("Process terminated")
                break
            time.sleep(0.01)

        # Terminate the process
        logger.debug("Terminating MCP server process")
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            logger.warning("Process did not terminate gracefully, killing")
            process.kill()

        # Check for errors
        stderr = process.stderr.read()
        if stderr:
            logger.error(f"Server error: {stderr}")

        # Return the last valid JSON response
        if output:
            return output[-1]
        else:
            logger.error("No valid response received")
            return None

    except Exception as e:
        logger.error(f"Error communicating with MCP server: {e}")
        return None

def resolve_library_id(library_name):
    """Resolve a general library name to a Context7-compatible library ID."""
    config = load_config()
    server_config = config.get("mcp_server", {})
    command = server_config.get("command", "npx")
    args = server_config.get("args", ["-y", "@upstash/context7-mcp@latest"])
    timeout = server_config.get("timeout", 30)
    
    # Construct MCP request for resolve-library-id tool
    request_data = {
        "tool": "resolve-library-id",
        "args": {
            "libraryName": library_name
        }
    }
    
    # Communicate with the server
    response = communicate_with_mcp_server(command, args, request_data, timeout)
    
    if not response or 'result' not in response:
        logger.error(f"Failed to resolve library ID for '{library_name}'")
        return None
    
    return response.get('result')

def fetch_documentation(library_id, topic="", tokens=5000):
    """Fetch JSON documentation from an MCP server."""
    # Load server configuration
    config = load_config()
    server_config = config.get("mcp_server", {})
    command = server_config.get("command", "npx")
    args = server_config.get("args", ["-y", "@upstash/context7-mcp@latest"])
    timeout = server_config.get("timeout", 30)
    
    # Check if we need to resolve the library ID first
    if '/' not in library_id:
        logger.info(f"Resolving library ID for '{library_id}'")
        resolved_id = resolve_library_id(library_id)
        if resolved_id:
            library_id = resolved_id
            logger.info(f"Resolved to '{library_id}'")
        else:
            logger.warning(f"Could not resolve library ID. Using original: '{library_id}'")

    # Construct MCP request for get-library-docs tool
    request_data = {
        "tool": "get-library-docs",
        "args": {
            "context7CompatibleLibraryID": library_id,
            "topic": topic,
            "tokens": max(tokens, 5000)  # Ensure minimum of 5000 tokens
        }
    }

    # Communicate with the server
    logger.info(f"Fetching documentation for '{library_id}'{' on topic ' + topic if topic else ''}")
    response = communicate_with_mcp_server(command, args, request_data, timeout)

    if not response:
        logger.error("No valid response received from the server")
        return None

    # Format output for Aider compatibility
    aider_output = {
        "content": json.dumps(response, indent=2),  # Aider expects a content field
        "library": response.get("library", ""),
        "snippets": response.get("snippets", []),
        "totalTokens": response.get("totalTokens", 0),
        "lastUpdated": response.get("lastUpdated", "")
    }

    # Print JSON output
    print(json.dumps(aider_output, indent=2))
    return aider_output

def list_supported_libraries():
    """List all libraries supported by Context7."""
    print("Fetching list of supported libraries from Context7...")
    print("This feature is not yet implemented. Please check https://context7.com for supported libraries.")
    return

def main():
    # Set up command-line argument parsing
    parser = argparse.ArgumentParser(description="Aider MCP client for fetching library documentation, defaulting to Context7.")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Fetch command
    fetch_parser = subparsers.add_parser("fetch", help="Fetch JSON documentation for a library")
    fetch_parser.add_argument("library_id", help="Library ID or name (e.g., vercel/nextjs or just nextjs)")
    fetch_parser.add_argument("--topic", default="", help="Topic to filter documentation (optional)")
    fetch_parser.add_argument("--tokens", type=int, default=5000, help="Maximum tokens (default: 5000)")
    
    # Resolve command
    resolve_parser = subparsers.add_parser("resolve", help="Resolve a library name to a Context7-compatible ID")
    resolve_parser.add_argument("library_name", help="Library name to resolve (e.g., nextjs)")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List supported libraries")
    
    # Global options
    parser.add_argument("-v", "--version", action="store_true", help="Show version information")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    # Set debug logging if requested
    if hasattr(args, 'debug') and args.debug:
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")

    if args.version:
        verbose()
        return

    if not args.command:
        verbose()
        return

    if args.command == "fetch":
        if hasattr(args, 'tokens') and args.tokens <= 0:
            logger.error("Error: Tokens must be a positive integer")
            return
        fetch_documentation(args.library_id, args.topic, args.tokens)
    
    elif args.command == "resolve":
        resolved = resolve_library_id(args.library_name)
        if resolved:
            print(f"Resolved '{args.library_name}' to: {resolved}")
        else:
            print(f"Could not resolve library name: {args.library_name}")
    
    elif args.command == "list":
        list_supported_libraries()

if __name__ == "__main__":
    main()
