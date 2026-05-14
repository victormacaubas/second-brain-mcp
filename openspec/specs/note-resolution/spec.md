### Requirement: Read note by file path

The `read_note` tool SHALL accept a relative path from vault root and return the note's full markdown content plus parsed frontmatter metadata.

#### Scenario: Valid relative path provided

- **WHEN** user calls `read_note(identifier="Concepts/mcp-and-agent-fundamentals.md")`
- **THEN** system returns the full content of that file and a metadata object with `title`, `date`, `description`, `tags`, and `aliases` extracted from frontmatter

#### Scenario: Path does not exist

- **WHEN** user calls `read_note(identifier="Concepts/nonexistent.md")`
- **THEN** system returns an error: "Note not found at 'Concepts/nonexistent.md'. Use search_vault() to find notes by keyword, or list_folder('Concepts') to browse available notes."

### Requirement: Read note by filename stem

The `read_note` tool SHALL accept a filename stem (without `.md` extension or folder path) and resolve it to the matching note anywhere in the vault.

#### Scenario: Unique stem provided

- **WHEN** user calls `read_note(identifier="mcp-and-agent-fundamentals")`
- **THEN** system locates `Concepts/mcp-and-agent-fundamentals.md` and returns its content and metadata

#### Scenario: Ambiguous stem matches multiple files

- **WHEN** user calls `read_note(identifier="design")` and multiple files named `design.md` exist in different project folders
- **THEN** system returns an error listing all matches: "Multiple notes match 'design'. Specify the full path: Projects/airflow-status-page-poc/design.md, Projects/dse-4740-sigma-public-alb/design.md. Or use search_vault('design') to see descriptions."

### Requirement: Read note by alias

The `read_note` tool SHALL accept an alias string and resolve it by scanning frontmatter `aliases:` fields across vault notes.

#### Scenario: Alias resolves to a single note

- **WHEN** user calls `read_note(identifier="MCP and Agents Learning Notes")`
- **THEN** system finds the note with that alias in its frontmatter and returns its content and metadata

#### Scenario: Alias not found

- **WHEN** user calls `read_note(identifier="Unknown Alias XYZ")`
- **THEN** system returns an error: "No note found with identifier 'Unknown Alias XYZ'. It didn't match any path, filename, or alias. Use search_vault('Unknown Alias XYZ') to search by content."

### Requirement: Success result includes a next-step hint

On a successful read, `read_note` SHALL append a hint that helps the model navigate from here.

#### Scenario: Note with tags

- **WHEN** `read_note` successfully returns a note that has tags
- **THEN** the response includes a trailing hint such as: "Use search_vault(query=<tag>) to find related notes, or list_folder(<parent_folder>) to browse this folder."

### Requirement: Metadata is always returned alongside content

The `read_note` tool SHALL always return both the raw markdown body (without frontmatter) and a structured metadata object parsed from YAML frontmatter.

#### Scenario: Note with complete frontmatter

- **WHEN** user reads a note that has title, date, description, tags, and aliases in frontmatter
- **THEN** system returns `metadata: {title, date, description, tags, aliases}` and `content` (markdown body without the YAML block)

#### Scenario: Note with minimal frontmatter

- **WHEN** user reads a note that only has `title` in frontmatter
- **THEN** system returns `metadata: {title, date: null, description: null, tags: [], aliases: []}` with missing fields as null/empty, and `content` as the markdown body
