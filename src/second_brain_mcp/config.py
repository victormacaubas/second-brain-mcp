from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Config:
    vault_path: Path

    def __post_init__(self) -> None:
        if not self.vault_path.exists():
            raise ValueError(
                f"VAULT_PATH '{self.vault_path}' does not exist. "
                "Set the VAULT_PATH environment variable to the root of your Obsidian vault."
            )
        if not self.vault_path.is_dir():
            raise ValueError(
                f"VAULT_PATH '{self.vault_path}' is not a directory. "
                "Set the VAULT_PATH environment variable to the root of your Obsidian vault."
            )


def load_config() -> Config:
    """Load and validate config from environment.

    Raises:
        ValueError: If VAULT_PATH is not set or points to a non-existent directory.
    """
    raw = os.environ.get("VAULT_PATH")
    if not raw:
        raise ValueError(
            "VAULT_PATH environment variable is not set. "
            "Set it to the root of your Obsidian vault, e.g.: "
            "export VAULT_PATH=~/Documents/Personal_Projects/llm-second-brain"
        )
    return Config(vault_path=Path(raw).expanduser().resolve())
