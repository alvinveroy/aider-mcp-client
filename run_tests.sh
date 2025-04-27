#!/bin/bash

# Install pytest if not already installed
pip install pytest pytest-cov

# Run tests with coverage
python -m pytest tests/ --cov=aider_mcp_client --cov-report=term-missing

echo "Tests completed!"
