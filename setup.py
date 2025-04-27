from setuptools import setup, find_packages

# This file is needed for compatibility with older pip versions
# The actual configuration is in pyproject.toml
setup(
    name="aider-mcp-client",
    version="0.0.1a0",  # PEP 440 compliant version (will be auto-updated)
    packages=find_packages(),
    include_package_data=True,
    install_requires=["requests>=2.25.0"],
    entry_points={
        "console_scripts": [
            "aider-mcp-client=aider_mcp_client.client:main",
            "aider_mcp_client=aider_mcp_client.client:main",
        ],
    },
)
