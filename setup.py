from setuptools import setup, find_packages

# This file is needed for compatibility with older pip versions
# The actual configuration is in pyproject.toml
setup(
    name="aider-mcp-client",
    use_scm_version={
        "write_to": "aider_mcp_client/_version.py",
        "version_scheme": "python-simplified-semver",
        "local_scheme": "no-local-version",
        "fallback_version": "0.1.0"
    },
    setup_requires=["setuptools_scm[toml]>=8.0"],
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
