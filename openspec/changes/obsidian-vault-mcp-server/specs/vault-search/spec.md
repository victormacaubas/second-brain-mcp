## ADDED Requirements

### Requirement: Search vault by keyword query

The `search_vault` tool SHALL accept a `query` string and return matching notes ranked by relevance. It SHALL first scan `INDEX.md` for matches against titles, aliases, descriptions, and tags. If INDEX yields fewer than 3 results, it SHALL fall back to `grep -r` across vault markdown files.

#### Scenario: Query matches note title in INDEX

- **WHEN** user calls `search_vault(query="airflow")`
- **THEN** system returns all notes whose title, alias, description, or tags contain "airflow", with each result including `title`, `path`, `description`, and `tags`

#### Scenario: Query matches alias in INDEX

- **WHEN** user calls `search_vault(query="CoT-ToT")`
- **THEN** system returns the note with alias "CoT-ToT" (resolves to `chain-of-thought-and-tree-of-thought.md`)

#### Scenario: INDEX yields insufficient results, grep fallback triggers

- **WHEN** user calls `search_vault(query="ephemeral keyring")` and INDEX contains no matches
- **THEN** system falls back to grep across vault files (excluding `.git`, `.obsidian`, `.venv`, `.claude`, `inbox`, `openspec`) and returns matching file paths with surrounding context

#### Scenario: No results found anywhere

- **WHEN** user calls `search_vault(query="nonexistent-topic-xyz")` and neither INDEX nor grep finds matches
- **THEN** system returns an empty result with a message: "No notes found matching 'nonexistent-topic-xyz'. Try broader terms or use list_folder() to browse by category."

### Requirement: Search results are capped

The `search_vault` tool SHALL return at most 20 results per call to avoid overwhelming the LLM context.

#### Scenario: Many matches found

- **WHEN** a query matches more than 20 notes
- **THEN** system returns the top 20 results and includes a note: "Showing 20 of N matches. Narrow your query for more specific results."

### Requirement: Search excludes inbox

The `search_vault` tool SHALL never return results from the `inbox/` folder, consistent with the vault's rule that inbox is not a source of truth.

#### Scenario: Query term exists only in inbox

- **WHEN** user calls `search_vault(query="draft-meeting-notes")` and the term only appears in `inbox/`
- **THEN** system returns no results (inbox is excluded from search)
