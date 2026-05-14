from __future__ import annotations

import logging

from mcp.server.fastmcp import FastMCP

from second_brain_mcp.config import load_config

logger = logging.getLogger(__name__)

config = load_config()
mcp = FastMCP("second-brain-mcp")


@mcp.tool()
def hello() -> str:
    """Verify the server is running. Returns a greeting with the configured vault path."""
    return f"second-brain-mcp is running. Vault: {config.vault_path}"


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
