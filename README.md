# MCP Client

A Python client for interacting with MCP (Model Control Protocol) servers, with Aider integration support.

## Features

- Simple configuration via JSON
- Command-line interface
- Aider-compatible JSON output
- Mock server responses for development

## Installation

```bash
pip install git+https://github.com/[your-username]/mcp_client.git
```

For development:
```bash
git clone https://github.com/[your-username]/mcp_client.git
cd mcp_client
pip install -e .
```

## Usage

Basic command structure:
```bash
python -m mcp_client.mcp_client.client <command> [args...]
```

Example commands:
```bash
# Get documentation
python -m mcp_client.mcp_client.client get_documentation

# Run with custom server
python -m mcp_client.mcp_client.client --server MyServer get_status
```

## Configuration

Default configuration (stored in `mcp_client/config.json`):
```json
{
    "server": "Context7",
    "host": "localhost",
    "port": 8000,
    "timeout": 30
}
```

Override defaults by creating a custom config file:
```bash
python -m mcp_client.mcp_client.client --config /path/to/config.json <command>
```

## Aider Integration

The client outputs JSON in Aider-compatible format:
```json
{
    "server": "Context7",
    "status": "success",
    "response": "Command output here"
}
```

## Development

### Running Tests
```bash
python -m unittest discover mcp_client/tests
```

### Code Structure
- `client.py`: Main CLI implementation
- `config.json`: Default configuration
- `tests/`: Unit tests

### Contributing
1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## License
MIT - See [LICENSE](LICENSE) for details.
