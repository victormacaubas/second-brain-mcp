from __future__ import annotations

from dataclasses import dataclass

EXCLUDED_DIRS = frozenset([".git", ".obsidian", ".venv", ".claude", "inbox", "openspec"])
KNOWLEDGE_FOLDERS = ["Concepts", "Guides", "Projects", "Systems", "Topics"]
VALID_PREFIXES = frozenset(["article", "convo", "note", "meeting"])
MAX_SEARCH_RESULTS = 20
INDEX_FALLBACK_THRESHOLD = 3  # trigger grep when INDEX yields fewer than this many results


@dataclass
class IndexEntry:
    wikilink: str  # identifier usable with read_note (stem or relative path without .md)
    title: str
    description: str
    tags: list[str]
    aliases: list[str]


@dataclass
class NoteMetadata:
    title: str
    date: str | None
    description: str | None
    tags: list[str]
    aliases: list[str]


@dataclass
class Note:
    relative_path: str  # e.g. "Concepts/mcp-and-agent-fundamentals.md"
    content: str        # markdown body without the YAML frontmatter block
    metadata: NoteMetadata


@dataclass
class FolderItem:
    path: str           # relative path from vault root
    title: str
    description: str | None


@dataclass
class TopLevelFolder:
    name: str
    note_count: int


@dataclass
class SearchResult:
    path: str           # relative path usable with read_note
    title: str
    description: str
    tags: list[str]
    match_source: str   # "index" or "grep"


def empty_metadata(stem: str) -> NoteMetadata:
    return NoteMetadata(title=stem, date=None, description=None, tags=[], aliases=[])
