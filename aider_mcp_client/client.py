import subprocess
import json
import argparse
import sys
import time
import os
from pathlib import Path

def load_config():
    """Load MCP server configuration from ~/.aider-mcp-client/config.json or return default."""
    default_config = {
        "mcp_server": {
            "command": "npx",
            "args": ["-y", "@upstash/context7-mcp@latest"],
            "tool": "fetch_documentation"
        }
    }
    config_path = Path.home() / ".aider-mcp-client" / "config.json"
    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            return config
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading config: {e}. Using default Context7 server.", file=sys.stderr)
    return default_config

def communicate_with_mcp_server(command, args, request_data, timeout=30):
    """Communicate with an MCP server via stdio."""
    try:
        # Start the MCP server process
        process = subprocess.Popen(
            [command] + args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8'
        )

        # Send JSON request to the server's stdin
        process.stdin.write(json.dumps(request_data) + '\n')
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
                    if isinstance(json_data, dict) and 'library' in json_data:
                        break
                except json.JSONDecodeError:
                    continue
            if process.poll() is not None:
                break
            time.sleep(0.01)

        # Terminate the process
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()

        # Check for errors
        stderr = process.stderr.read()
        if stderr:
            print(f"Server error: {stderr}", file=sys.stderr)

        # Return the last valid JSON response
        return output[-1] if output else None

    except Exception as e:
        print(f"Error communicating with MCP server: {e}", file=sys.stderr)
        return None

def fetch_documentation(library_id, topic="", tokens=5000):
    """Fetch JSON documentation from an MCP server."""
    # Load server configuration
    config = load_config()
    server_config = config.get("mcp_server", {})
    command = server_config.get("command", "npx")
    args = server_config.get("args", ["-y", "@upstash/context7-mcp@latest"])
    tool = server_config.get("tool", "fetch_documentation")

    # Construct MCP request
    request_data = {
        "tool": tool,
        "args": {
            "library_id": library_id,
            "topic": topic,
            "tokens": tokens
        }
    }

    # Communicate with the server
    response = communicate_with_mcp_server(command, args, request_data)

    if not response:
        print("No valid response received from the server", file=sys.stderr)
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

def main():
    # Set up command-line argument parsing
    parser = argparse.ArgumentParser(description="Aider MCP client for fetching library documentation, defaulting to Context7.")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    fetch_parser = subparsers.add_parser("fetch", help="Fetch JSON documentation for a library")
    fetch_parser.add_argument("library_id", help="Library ID (e.g., vercel/nextjs)")
    fetch_parser.add_argument("--topic", default="", help="Topic to filter documentation (optional)")
    fetch_parser.add_argument("--tokens", type=int, default=5000, help="Maximum tokens (default: 5000)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    if args.command == "fetch":
        if args.tokens <= 0:
            print("Error: Tokens must be a positive integer", file=sys.stderr)
            return
        fetch_documentation(args.library_id, args.topic, args.tokens)

if __name__ == "__main__":
    main()
