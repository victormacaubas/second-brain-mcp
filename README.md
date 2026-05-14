# second-brain-mcp

MCP server that exposes a personal Obsidian vault over stdio. Lets Claude Desktop, Claude Code, or any stdio-capable MCP client search, read, browse, and write to the vault without depending on a running Obsidian instance.

## Tools

| Tool | What it does |
|---|---|
| `search_vault` | Keyword search — INDEX.md first, grep fallback if fewer than 3 INDEX hits. Excludes inbox. |
| `read_note` | Read a note by relative path, filename stem, or frontmatter alias. Returns metadata + body. |
| `list_folder` | Top-level folder summary (no arg) or note listing for a specific folder. |
| `create_inbox_note` | Write a new note to `inbox/` with auto-generated frontmatter and optional prefix. |

## Prerequisites

- [uv](https://docs.astral.sh/uv/) — Python package manager and runner. Install with:
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```
- [Claude CLI](https://claude.ai/download) — only needed if installing for Claude Code (not required for Claude Desktop)

> **Note:** You do not need to install Python manually. `uv` will download and manage Python 3.13 automatically when the server first runs.

## Installation

```bash
git clone https://github.com/victormacaubas/second-brain-mcp.git
cd second-brain-mcp
uv sync
```

## Quick start

The install script registers the server with your preferred Claude client in one command:

```bash
# Claude Code — current project only (default)
./install.sh ~/path/to/your/vault

# Claude Code — available in all sessions
./install.sh ~/path/to/your/vault --global

# Claude Desktop
./install.sh ~/path/to/your/vault --desktop
```

Run `./install.sh --help` for full usage details.

## Connecting to Claude Code

### Project-scoped (default)

Registers the server for the current project directory. Writes to `.claude/settings.json`:

```bash
./install.sh /absolute/path/to/vault
```

### Global

Registers the server for all Claude Code sessions. Writes to `~/.claude/settings.json`:

```bash
./install.sh /absolute/path/to/vault --global
```

### Verify

After installing, restart Claude Code and run:

```bash
claude mcp list
```

You should see `second-brain-mcp` listed with status `connected`.

## Connecting to Claude Desktop

```bash
./install.sh /absolute/path/to/vault --desktop
```

This merges the server entry into your Claude Desktop config file without touching other settings. Quit and reopen Claude Desktop to activate — the server will appear in the MCP tools menu (hammer icon).

**Config file locations:**

| OS | Path |
|---|---|
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Linux | `~/.config/Claude/claude_desktop_config.json` |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |

> **Troubleshooting:** If the server doesn't connect, check `~/Library/Logs/Claude/mcp*.log` (macOS) for startup errors. The most common issues are an incorrect vault path or `uv` not being found at the expected location.

## Manual configuration

If you prefer not to use the install script, you can configure things manually.

### Claude Code (via CLI)

```bash
claude mcp add second-brain-mcp \
  --scope project \
  --transport stdio \
  -e VAULT_PATH=/absolute/path/to/vault \
  -- "$(which uv)" run --directory /absolute/path/to/second-brain-mcp second-brain-mcp
```

Change `--scope project` to `--scope user` for global installation.

The `--` separates Claude's own flags from the command it will run as a subprocess. Everything after `--` is what gets executed when the server starts:
- `$(which uv)` — full path to the uv binary
- `run --directory <path>` — tells uv where to find the project (pyproject.toml)
- `second-brain-mcp` — the entry point name from `[project.scripts]`

### Claude Desktop (manual JSON)

Edit the config file at the path for your OS (see table above) and add:

```json
{
  "mcpServers": {
    "second-brain-mcp": {
      "command": "/path/to/uv",
      "args": [
        "run",
        "--directory", "/absolute/path/to/second-brain-mcp",
        "second-brain-mcp"
      ],
      "env": {
        "VAULT_PATH": "/absolute/path/to/vault"
      }
    }
  }
}
```

If the file already exists with other servers, merge the `second-brain-mcp` entry into the existing `mcpServers` object.

## Running standalone (for testing)

The server speaks MCP over stdio — it is not meant to be invoked directly. But you can verify it starts:

```bash
VAULT_PATH=~/path/to/vault uv run second-brain-mcp
```

It will hang waiting for stdio input — that's correct. Press `Ctrl+C` to exit.

## Development

Test with MCP Inspector before connecting to a real model:

```bash
VAULT_PATH=~/path/to/vault \
  npx @modelcontextprotocol/inspector \
  uv run --directory /absolute/path/to/second-brain-mcp second-brain-mcp
```

## Vault conventions

The server expects the vault to follow these conventions:

- Kebab-case `.md` filenames
- YAML frontmatter on every note (`title`, `date`, `description`, `tags`, `aliases`)
- `INDEX.md` at vault root with title/alias/description/tag entries per note
- `inbox/` as staging — excluded from search, only target for writes

Writes go to `inbox/` only.
