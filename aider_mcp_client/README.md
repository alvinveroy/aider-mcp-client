# Aider MCP Client

A Python client for interacting with MCP (Model Control Protocol) servers, specifically designed to work with [Aider](https://aider.chat) and [Context7](https://context7.com).

## Installation

```bash
pip install aider-mcp-client
```

## Usage

### Basic Usage

```bash
# Fetch documentation for a library
mcp_client fetch nextjs

# Fetch documentation with a specific topic
mcp_client fetch vercel/nextjs --topic routing

# Resolve a library name to a Context7-compatible ID
mcp_client resolve nextjs

# Show version information
mcp_client -v
```

### Integration with Aider

This client is designed to be used with Aider via the `/run` command:

```
/run mcp_client fetch nextjs --topic api-routes
```

### Configuration

The client looks for configuration in the following locations:
1. `./.aider-mcp-client/config.json` (current directory)
2. `~/.aider-mcp-client/config.json` (user home directory)

Example configuration:

```json
{
  "mcp_server": {
    "command": "npx",
    "args": ["-y", "@upstash/context7-mcp@latest"],
    "tool": "get-library-docs",
    "timeout": 30,
    "enabled": true
  }
}
```

## Available Commands

- `fetch`: Fetch documentation for a library
- `resolve`: Resolve a library name to a Context7-compatible ID
- `list`: List supported libraries (coming soon)

## License

MIT
