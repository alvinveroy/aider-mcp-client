# MCP Client

A Python client for interacting with MCP (Model Control Protocol) servers, with Aider integration support. This client primarily focuses on fetching documentation from Context7 MCP servers.

[![PyPI version](https://badge.fury.io/py/mcp_client.svg)](https://badge.fury.io/py/mcp_client)

## Features

- Simple configuration via JSON
- Command-line interface
- Aider-compatible JSON output
- Integration with Context7 MCP servers

## Installation

From PyPI:
```bash
pip install mcp_client
```

From GitHub:
```bash
pip install git+https://github.com/alvinveroy/mcp_client.git
```

For development:
```bash
git clone https://github.com/alvinveroy/mcp_client.git
cd mcp_client
pip install -e .
```

## Usage

After installation, you can use the command-line interface:

```bash
mcp_client <command> [args...]
```

Or as a module:
```bash
python -m mcp_client.client <command> [args...]
```

Example commands:
```bash
# Show version information
mcp_client
# or
mcp_client -v
# or
mcp_client --version

# Fetch documentation for a specific library
mcp_client fetch vercel/nextjs

# Fetch documentation with a specific topic and token limit
mcp_client fetch vercel/nextjs --topic "routing" --tokens 10000
```

## Configuration

The client uses a configuration file located at `~/.mcp_client/config.json`. If this file doesn't exist, default settings are used.

Default configuration:
```json
{
  "mcp_server": {
    "command": "npx",
    "args": ["-y", "@upstash/context7-mcp@latest"],
    "tool": "fetch_documentation"
  }
}
```

You can create a custom configuration file:
```bash
mkdir -p ~/.mcp_client
echo '{
  "mcp_server": {
    "command": "npx",
    "args": ["-y", "@upstash/context7-mcp@latest"],
    "tool": "fetch_documentation"
  }
}' > ~/.mcp_client/config.json
```

## Available Commands

- `version`: Display version information
  ```bash
  mcp_client
  # or
  mcp_client -v
  # or
  mcp_client --version
  ```

- `fetch`: Retrieve documentation for a specific library
  ```bash
  mcp_client fetch <library_id> [--topic "topic"] [--tokens 5000]
  ```
  or
  ```bash
  python -m mcp_client.client fetch <library_id> [--topic "topic"] [--tokens 5000]
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
python -m unittest discover tests
```

### Code Structure
- `mcp_client/client.py`: Main client implementation with CLI interface
- `mcp_client/config.json`: Default configuration template
- `tests/`: Unit tests

### Publishing to PyPI

To publish updates to PyPI:

```bash
# Install build tools
pip install --upgrade build twine

# Build the package
python -m build

# Upload to PyPI
python -m twine upload dist/*
```

For test uploads, use the TestPyPI repository:
```bash
python -m twine upload --repository testpypi dist/*
```

You can install from TestPyPI with:

```bash
pip install --index-url https://test.pypi.org/simple/ aider-mcp-client
```

### Contributing
1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## License
MIT - See [LICENSE](LICENSE) for details.
