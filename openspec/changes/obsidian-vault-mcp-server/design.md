## Context

The Obsidian vault (`~/Documents/Personal_Projects/llm-second-brain`) is a 106-note knowledge base with strict conventions: kebab-case filenames, YAML frontmatter on every note, an auto-generated `INDEX.md` with titles/aliases/descriptions/tags, and wikilink-based cross-references. Currently only accessible to Claude Code via installed skills (`obsidian-cli`, `obsidian-markdown`). Other MCP clients (Claude Desktop, Codex Desktop) have no vault access.

This is a learning project — the primary constraint is that the implementation should surface MCP concepts clearly, not be optimized for production scale.

## Goals / Non-Goals

**Goals:**
- Expose vault read/write via MCP tools usable from any stdio-capable client
- Encode the vault's retrieval protocol (INDEX-first → grep fallback) as tool behavior
- Produce tool descriptions that guide LLM behavior without client-side prompt instructions
- Follow python-engineering-standards for project layout and code style
- Keep the server self-contained (no dependency on running Obsidian app)

**Non-Goals:**
- Production-grade error recovery or observability
- HTTP/SSE transport or multi-user access
- Full placement logic for writes (inbox-only is the boundary)
- Automated tests (MCP Inspector + real model usage is the feedback loop)
- Graph traversal or related-note discovery

## Decisions

### 1. FastMCP over low-level Server API

FastMCP (decorator-based, FastAPI-like) keeps tool definitions close to their implementations and uses docstrings as tool descriptions. The low-level API adds boilerplate without teaching different concepts.

**Alternative considered:** Low-level `mcp.server.Server` — more verbose, same capabilities, no benefit for a 4-tool server.

### 2. INDEX.md as primary search index

INDEX.md contains every note's title, aliases, description, and tags in a grep-friendly format. Parsing it gives structured search results without building a custom index or depending on external services.

**Alternative considered:** Full-text grep only — loses structured metadata (tags, aliases, descriptions). SQLite FTS — over-engineered for 106 notes and adds a build/sync step.

### 3. Alias resolution via frontmatter scan

`read_note` accepts a filename stem or alias. On miss, it scans frontmatter `aliases:` fields across the vault to resolve. For 106 notes this is fast enough (<100ms). A lookup cache could be added later if the vault grows.

**Alternative considered:** Pre-built alias→path map loaded at server startup — faster but stale if vault changes during a session. Acceptable trade-off for v2.

### 4. Inbox-only writes

All write operations target `inbox/` exclusively. This mirrors the vault's "courier rule" — content lands in inbox, `/process-inbox` files it later. Prevents the MCP server from needing to understand the full placement decision tree, hub updates, or INDEX regeneration.

**Alternative considered:** Full placement writes with decision tree — complex, error-prone, and out of scope for a learning project.

### 5. Config via environment variable

`VAULT_PATH` env var points to the vault root. Keeps the server portable across machines without hardcoding paths. The config module validates the path exists at startup and fails fast with a clear error.

**Alternative considered:** CLI argument (`--vault-path`) — viable, but env var is idiomatic for MCP servers (matches how clients pass config). Could support both later.

### 6. src/ layout with server/vault/config separation

- `config.py`: frozen dataclass loaded from env, validated at construction
- `vault.py`: filesystem operations (parse INDEX, read frontmatter, grep, write inbox). Accepts config via constructor injection.
- `server.py`: FastMCP app definition, tool decorators, error formatting. Composition root that wires config → vault → tools.

This separation means vault logic is testable independently of MCP transport (future benefit) and keeps server.py focused on tool descriptions and error UX.

## Risks / Trade-offs

- **INDEX.md staleness** → If vault changes while server is running, INDEX may be out of date. Mitigation: re-read INDEX on each `search_vault` call (file is small, IO is cheap). Acceptable for a local stdio server.
- **Alias scan performance at scale** → Scanning all frontmatter for alias resolution is O(n) in note count. Mitigation: 106 notes is trivial. If vault grows past ~500 notes, add a startup-built alias map with file-watcher invalidation.
- **No validation of inbox writes** → `create_inbox_note` doesn't enforce vault frontmatter completeness. Mitigation: it adds minimal required fields (title, date, tags). `/process-inbox` handles the rest.
- **stdio transport limits concurrency** → Single client at a time. Mitigation: this is a personal tool, not a service. Acceptable.
