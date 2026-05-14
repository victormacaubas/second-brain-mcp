### Requirement: Create a note in inbox with prefix

The `create_inbox_note` tool SHALL create a new markdown file in the vault's `inbox/` folder with a kebab-case filename and optional prefix.

#### Scenario: Create note with article prefix

- **WHEN** user calls `create_inbox_note(title="React Server Components Deep Dive", content="...", prefix="article")`
- **THEN** system creates `inbox/article-react-server-components-deep-dive.md` and returns the created filepath

#### Scenario: Create note with no prefix

- **WHEN** user calls `create_inbox_note(title="Quick thought on caching", content="...")`
- **THEN** system creates `inbox/quick-thought-on-caching.md` (no prefix) and returns the created filepath

#### Scenario: Create note with meeting prefix

- **WHEN** user calls `create_inbox_note(title="Sprint Planning 2026-05-14", content="...", prefix="meeting")`
- **THEN** system creates `inbox/meeting-sprint-planning-2026-05-14.md` and returns the created filepath

### Requirement: Auto-generate minimal frontmatter

The `create_inbox_note` tool SHALL prepend YAML frontmatter with `title`, `date` (today), and `tags: [inbox]` to every created note.

#### Scenario: Frontmatter is added automatically

- **WHEN** user calls `create_inbox_note(title="My Note", content="Some content")`
- **THEN** the created file starts with:
  ```yaml
  ---
  title: My Note
  date: 2026-05-14
  tags:
    - inbox
  ---
  ```
  followed by the provided content

### Requirement: Title to kebab-case conversion

The `create_inbox_note` tool SHALL convert the title to kebab-case for the filename: lowercase, replace spaces and special characters with hyphens, collapse multiple hyphens, strip leading/trailing hyphens.

#### Scenario: Title with special characters

- **WHEN** user calls `create_inbox_note(title="What's New in Python 3.13?", content="...")`
- **THEN** system creates a file named `whats-new-in-python-3-13.md` (or with prefix: `note-whats-new-in-python-3-13.md`)

### Requirement: Prevent filename collisions

The `create_inbox_note` tool SHALL NOT overwrite existing files. If a file with the target name already exists, it SHALL append a numeric suffix.

#### Scenario: File already exists

- **WHEN** user calls `create_inbox_note(title="Meeting Notes", content="...", prefix="meeting")` and `inbox/meeting-meeting-notes.md` already exists
- **THEN** system creates `inbox/meeting-meeting-notes-1.md` and returns the actual created filepath

### Requirement: Success result includes a next-step hint

On successful creation, `create_inbox_note` SHALL return the created path and a reminder about the inbox workflow.

#### Scenario: Note created successfully

- **WHEN** `create_inbox_note` writes a file successfully
- **THEN** the response is: "Created inbox/meeting-sprint-planning.md. Run /process-inbox in Obsidian to file it into the vault."

### Requirement: Validate prefix values

The `create_inbox_note` tool SHALL accept only valid prefix values: `"article"`, `"convo"`, `"note"`, `"meeting"`. Invalid prefixes SHALL produce a clear error.

#### Scenario: Invalid prefix provided

- **WHEN** user calls `create_inbox_note(title="Test", content="...", prefix="blog")`
- **THEN** system returns an error: "Invalid prefix 'blog'. Valid prefixes: article, convo, note, meeting. Omit prefix for an unprefixed note."
