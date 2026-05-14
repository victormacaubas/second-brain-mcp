# second-brain-mcp

MCP server exposing an Obsidian vault over stdio. Learning project — first MCP server build.

## Stack

Python 3.13, FastMCP (`mcp` SDK), uv, stdio transport.

## Setup

```bash
uv sync
export VAULT_PATH=~/Documents/Personal_Projects/llm-second-brain
```

## Design Rules

- **Tool docstrings are prompts.** They're sent to the LLM verbatim as tool descriptions. Write them for a model, not a human. Include "use when", "don't use for", and parameter guidance.
- **Errors are prompts.** Every error must say: what went wrong, why, and what tool/action to try next. Never return raw exceptions.
- **Search protocol:** INDEX.md scan first → `grep -r` fallback (with exclusions). Never depend on obsidian-cli or a running Obsidian app.
- **Writes go to `inbox/` only.** Never write to knowledge folders (Concepts, Topics, Projects, etc.).
- **Config via `VAULT_PATH` env var.** Validated at startup — fail fast with clear message if missing or invalid.

## Vault Conventions (what the server must respect)

- Filenames: kebab-case only, `.md` extension
- Every note has YAML frontmatter: `title`, `date`, `description`, `tags`, `aliases`
- `inbox/` is staging — excluded from search, never treated as knowledge
- INDEX.md at vault root contains every note's title, aliases, description, tags (grep-friendly)
- Inbox prefixes: `article-`, `convo-`, `note-`, `meeting-`

## Development

Test with MCP Inspector (`npx @modelcontextprotocol/inspector`) before connecting to a real model.

## Non-goals

No tests, no HTTP transport, no delete/update of existing notes, no graph traversal, no obsidian-cli dependency.

## Code Style

Load the `/python-engineering-standards` skill before writing Python code.
