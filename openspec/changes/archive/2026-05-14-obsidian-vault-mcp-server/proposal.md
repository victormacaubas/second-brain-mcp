## Why

Learning project for building a first MCP server. The Obsidian vault at `~/Documents/Personal_Projects/llm-second-brain` has a well-defined retrieval protocol (INDEX.md → grep) and write convention (inbox-only), making it an ideal domain for a first tool surface. Secondary goal: expose vault access to Claude Desktop and Codex Desktop, which can't use Claude Code skills.

## What Changes

- New Python MCP server (`second-brain-mcp`) exposing four tools over stdio transport:
  - `search_vault` — smart search using INDEX.md scan + grep fallback
  - `read_note` — resolve notes by path, filename stem, or alias
  - `list_folder` — browse vault folder structure
  - `create_inbox_note` — write to inbox/ with proper prefix and frontmatter
- New `src/second_brain_mcp/` package with server, vault logic, and config modules
- `pyproject.toml` with `mcp` SDK dependency, managed by uv

## Capabilities

### New Capabilities

- `vault-search`: INDEX.md parsing, keyword matching against titles/aliases/descriptions/tags, grep fallback with exclusions
- `note-resolution`: Resolve note identifiers (path, stem, alias) through frontmatter parsing, return content + metadata
- `folder-listing`: List notes within vault folders with title/path/description from frontmatter
- `inbox-write`: Create notes in inbox/ with kebab-case naming, prefix convention, and auto-generated minimal frontmatter

### Modified Capabilities

_None — greenfield project._

## Impact

- New project files: `pyproject.toml`, `src/second_brain_mcp/{__init__,server,vault,config}.py`
- External dependency: `mcp` Python SDK (FastMCP)
- Reads from the Obsidian vault filesystem (read-only except inbox/)
- Config: `VAULT_PATH` environment variable required at runtime
- Registration: server added to Claude Desktop / Codex Desktop MCP config after build
