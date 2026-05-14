## 1. Project Scaffolding

- [x] 1.1 Initialize uv project with Python 3.13 (`uv init`, set `.python-version` to `3.13`, create venv with `uv venv`)
- [x] 1.2 Create `pyproject.toml` with project metadata, `mcp` SDK dependency, and Python 3.13 requirement
- [x] 1.3 Create `src/second_brain_mcp/__init__.py`
- [x] 1.4 Create `src/second_brain_mcp/config.py` with frozen dataclass reading `VAULT_PATH` from environment, validate path exists at construction
- [x] 1.5 Create minimal `src/second_brain_mcp/server.py` with FastMCP app and a single hello-world tool, verify it runs with MCP Inspector

## 2. Vault Read Logic

- [x] 2.1 Create `src/second_brain_mcp/vault.py` with `Vault` class that accepts config via constructor
- [x] 2.2 Implement INDEX.md parser: read file, extract entries with title, path, description, tags, aliases
- [x] 2.3 Implement frontmatter parser: read a note file, split YAML frontmatter from markdown body, return structured metadata + content
- [x] 2.4 Implement note resolution: accept identifier, try as path → stem search → alias scan, return content + metadata or structured error
- [x] 2.5 Implement folder listing: list `.md` files in a folder with frontmatter-derived title/description, handle top-level default and inbox exclusion

## 3. Search Implementation

- [x] 3.1 Implement INDEX-based search: keyword match against parsed INDEX entries (title, aliases, description, tags), rank by match quality
- [x] 3.2 Implement grep fallback: subprocess `grep -r` with exclusion list (`.git`, `.obsidian`, `.venv`, `.claude`, `inbox`, `openspec`), parse results into structured format
- [x] 3.3 Wire search logic: INDEX first, if <3 results trigger grep fallback, merge and deduplicate, cap at 20 results

## 4. Inbox Write Logic

- [x] 4.1 Implement title-to-kebab-case converter (lowercase, replace special chars, collapse hyphens)
- [x] 4.2 Implement inbox note creation: build filename with prefix, generate frontmatter (title, date, tags), write file, handle collision with numeric suffix
- [x] 4.3 Implement prefix validation (article, convo, note, meeting) with clear error on invalid values

## 5. Tool Wiring

- [x] 5.1 Wire `search_vault` tool in server.py with prompt-quality docstring, connect to vault search logic
- [x] 5.2 Wire `read_note` tool in server.py with prompt-quality docstring, connect to note resolution
- [x] 5.3 Wire `list_folder` tool in server.py with prompt-quality docstring, connect to folder listing
- [x] 5.4 Wire `create_inbox_note` tool in server.py with prompt-quality docstring, connect to inbox write logic

## 6. Integration & Registration

- [x] 6.1 Test all four tools via MCP Inspector (happy path + error cases)
- [x] 6.2 Register server with Claude Code (`claude mcp add`). Locally, just to this project folder, not global instalation.
- [x] 6.3 Register server with Claude Desktop (update MCP config JSON)
- [x] 6.4 Test with real model: ask Claude to search, read, browse, and create notes — iterate on tool descriptions based on observed behavior
