# Aider MCP Client

A Python client for interacting with MCP (Model Control Protocol) servers, with Aider integration support. This client primarily focuses on fetching documentation from Context7 MCP servers.

[![PyPI version](https://badge.fury.io/py/aider-mcp-client.svg)](https://badge.fury.io/py/aider-mcp-client)

## Features

- Simple configuration via JSON
- Command-line interface
- Aider-compatible JSON output
- Integration with Context7 MCP servers

## Installation

From PyPI:
```bash
pip install aider-mcp-client
```

From GitHub:
```bash
pip install git+https://github.com/alvinveroy/aider-mcp-client.git
```

For development:
```bash
git clone https://github.com/alvinveroy/aider-mcp-client.git
cd aider-mcp-client
pip install -e .
```

## Usage

After installation, you can use the command-line interface:

```bash
aider_mcp_client <command> [args...]
```

Or as a module:
```bash
python -m aider_mcp_client.client <command> [args...]
```

Example commands:
```bash
# Show version information
aider_mcp_client
# or
aider_mcp_client -v
# or
aider_mcp_client --version

# Fetch documentation for a specific library
aider_mcp_client fetch vercel/nextjs

# Fetch documentation with a specific topic and token limit
aider_mcp_client fetch vercel/nextjs --topic "routing" --tokens 10000
```

## Configuration

The client uses a configuration file located at `~/.aider-mcp-client/config.json`. If this file doesn't exist, default settings are used.

Default configuration:
```json
{
  "mcpServers": {
    "context7": {
      "command": "npx",
      "args": ["-y", "@upstash/context7-mcp@latest"],
      "enabled": true,
      "timeout": 30
    }
  }
}
```

You can create a custom configuration file:
```bash
mkdir -p ~/.aider-mcp-client
echo '{
  "mcpServers": {
    "context7": {
      "command": "npx",
      "args": ["-y", "@upstash/context7-mcp@latest"],
      "enabled": true,
      "timeout": 30
    }
  }
}' > ~/.aider-mcp-client/config.json
```

## Available Commands

- `version`: Display version information
  ```bash
  aider_mcp_client
  # or
  aider_mcp_client -v
  # or
  aider_mcp_client --version
  ```

- `fetch`: Retrieve documentation for a specific library
  ```bash
  aider_mcp_client fetch <library_id> [--topic "topic"] [--tokens 5000]
  ```
  or
  ```bash
  python -m aider_mcp_client.client fetch <library_id> [--topic "topic"] [--tokens 5000]
  ```

## Aider Integration

The client outputs JSON in Aider-compatible format:
```json
{
  "content": "...",
  "library": "library_name",
  "snippets": [...],
  "totalTokens": 5000,
  "lastUpdated": "timestamp"
}
```

## Development

### Running Tests
```bash
# Install pytest first
pip install pytest

# Then run the tests
python -m pytest tests/
```

You can also use unittest if you prefer:
```bash
python -m unittest discover tests
```

### Code Structure
- `aider_mcp_client/client.py`: Main client implementation with CLI interface
- `aider_mcp_client/config.json`: Default configuration template
- `tests/`: Unit tests


### Contributing
1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## License
MIT - See [LICENSE](LICENSE) for details.
