#!/usr/bin/env python3
"""
Main entry point for the aider_mcp_client package.
This allows running the package directly with 'python -m aider_mcp_client'
"""

from aider_mcp_client.client import async_main
import asyncio

if __name__ == "__main__":
    asyncio.run(async_main())
