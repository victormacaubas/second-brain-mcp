# second-brain-mcp

MCP server that exposes my personal Obsidian vault over stdio. Lets Claude Desktop, Codex Desktop, or any stdio-capable MCP client search, read, browse, and write to the vault without depending on a running Obsidian instance.

## Tools

| Tool | What it does |
|---|---|
| `search_vault` | Keyword search — INDEX.md first, grep fallback if fewer than 3 INDEX hits. Excludes inbox. |
| `read_note` | Read a note by relative path, filename stem, or frontmatter alias. Returns metadata + body. |
| `list_folder` | Top-level folder summary (no arg) or note listing for a specific folder. |
| `create_inbox_note` | Write a new note to `inbox/` with auto-generated frontmatter and optional prefix. |

## Setup

Requires Python 3.13 and [uv](https://docs.astral.sh/uv/).

```bash
git clone <repo>
cd second-brain-mcp
uv sync
export VAULT_PATH=~/Documents/Personal_Projects/llm-second-brain
```

## Running

```bash
VAULT_PATH=~/path/to/vault uv run second-brain-mcp
```

The server speaks MCP over stdio. It is not meant to be run directly — register it with a client (see below) and the client starts it as a subprocess.

## Claude Code (project-scoped)

Add `.claude/settings.json` to the project root:

```json
{
  "mcpServers": {
    "second-brain-mcp": {
      "command": "/opt/homebrew/bin/uv",
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

## Claude Desktop

Add the same `mcpServers` block to `~/Library/Application Support/Claude/claude_desktop_config.json` and restart Claude Desktop.

## Development

Test with MCP Inspector before connecting to a model:

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