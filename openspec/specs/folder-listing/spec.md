### Requirement: List notes in a specific vault folder

The `list_folder` tool SHALL accept an optional `folder` parameter and return notes within that folder, including each note's `title`, `path`, and `description` from frontmatter.

#### Scenario: List notes in a top-level folder

- **WHEN** user calls `list_folder(folder="Concepts")`
- **THEN** system returns all `.md` files in `Concepts/` with their title, relative path, and description parsed from frontmatter

#### Scenario: List notes in a nested project folder

- **WHEN** user calls `list_folder(folder="Projects/airflow-status-page-poc")`
- **THEN** system returns all `.md` files within that project folder (including capabilities subfolder) with title, path, and description

### Requirement: Default lists top-level vault structure

When called without a `folder` argument, the `list_folder` tool SHALL return the top-level vault folders with a count of notes in each.

#### Scenario: No folder argument provided

- **WHEN** user calls `list_folder()`
- **THEN** system returns a list of top-level folders: `[{name: "Concepts", note_count: N}, {name: "Guides", note_count: N}, {name: "Projects", note_count: N}, {name: "Systems", note_count: N}, {name: "Topics", note_count: N}]`

### Requirement: Folder not found error

The `list_folder` tool SHALL return a helpful error when the folder does not exist.

#### Scenario: Invalid folder path

- **WHEN** user calls `list_folder(folder="NonExistent")`
- **THEN** system returns an error: "Folder 'NonExistent' not found. Available top-level folders: Concepts, Guides, Projects, Systems, Topics. Use list_folder() without arguments to browse."

### Requirement: Success result includes a next-step hint

On any non-empty listing, `list_folder` SHALL append a hint that tells the model how to navigate deeper.

#### Scenario: Top-level listing returned

- **WHEN** `list_folder()` returns the top-level folder list
- **THEN** response includes a hint: "Use list_folder(folder=<name>) to browse a folder, or search_vault(query) to find notes by keyword."

#### Scenario: Folder notes listed

- **WHEN** `list_folder(folder="Concepts")` returns notes
- **THEN** response includes a hint: "Use read_note(identifier=<path>) to open a note."

### Requirement: Inbox folder is excluded

The `list_folder` tool SHALL NOT list `inbox/` as a browsable folder and SHALL refuse to list its contents.

#### Scenario: User attempts to list inbox

- **WHEN** user calls `list_folder(folder="inbox")`
- **THEN** system returns an error: "The inbox/ folder is a staging area and not browsable. Use list_folder() to see knowledge folders, or create_inbox_note() to write to inbox."
