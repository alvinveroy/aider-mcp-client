# Contributing to MCP Client

We welcome contributions from the community! Here's how to get started.

## Getting Started

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone git@github.com:your-username/mcp-client.git
   ```
3. Create a new branch for your changes:
   ```bash
   git checkout -b my-feature-branch
   ```

## Development Setup

1. Install development dependencies:
   ```bash
   pip install -e .[dev]
   ```

2. Run tests before making changes:
   ```bash
   pytest
   ```

3. Make your changes following the project's coding style.

## Submitting Changes

1. Ensure all tests pass:
   ```bash
   pytest
   ```

2. Lint your code:
   ```bash
   flake8 mcp_client
   ```

3. Commit your changes with a descriptive message:
   ```bash
   git commit -m "Add my awesome contribution"
   ```

4. Push to your fork:
   ```bash
   git push origin my-feature-branch
   ```

5. Open a Pull Request against the main repository's `main` branch.

## Code Style

- Follow PEP 8 guidelines
- Use type hints for all function signatures
- Keep docstrings up to date
- Write tests for new functionality

## Reporting Issues

When reporting bugs, please include:
- Steps to reproduce
- Expected behavior
- Actual behavior
- Version information

Thank you for contributing!
