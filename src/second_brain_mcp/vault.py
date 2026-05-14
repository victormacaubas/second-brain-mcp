from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from second_brain_mcp.config import Config

logger = logging.getLogger(__name__)

EXCLUDED_DIRS = frozenset([".git", ".obsidian", ".venv", ".claude", "inbox", "openspec"])
KNOWLEDGE_FOLDERS = ["Concepts", "Guides", "Projects", "Systems", "Topics"]


# ---------------------------------------------------------------------------
# Domain types
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Vault
# ---------------------------------------------------------------------------


class Vault:
    def __init__(self, config: Config) -> None:
        self._root = config.vault_path

    # ------------------------------------------------------------------
    # 2.2  INDEX.md parser
    # ------------------------------------------------------------------

    def parse_index(self) -> list[IndexEntry]:
        """Read INDEX.md and return all note entries found.

        Re-reads the file on every call so search results stay fresh when the
        vault changes while the server is running.
        """
        index_path = self._root / "INDEX.md"
        if not index_path.exists():
            logger.warning("INDEX.md not found at %s", index_path)
            return []

        entries: list[IndexEntry] = []
        for line in index_path.read_text(encoding="utf-8").splitlines():
            entry = _parse_index_line(line)
            if entry:
                entries.append(entry)
        return entries

    # ------------------------------------------------------------------
    # 2.3  Frontmatter parser
    # ------------------------------------------------------------------

    def parse_frontmatter(self, note_path: Path) -> tuple[NoteMetadata, str]:
        """Split YAML frontmatter from markdown body and return both.

        Args:
            note_path: Absolute path to a vault note.

        Returns:
            Tuple of (metadata, body). body is the markdown content with the
            YAML block stripped. Missing frontmatter fields default to
            None / empty list.

        Raises:
            FileNotFoundError: If note_path does not exist.
        """
        text = note_path.read_text(encoding="utf-8")

        if not text.startswith("---"):
            return _empty_metadata(note_path.stem), text

        end = text.find("\n---", 3)
        if end == -1:
            return _empty_metadata(note_path.stem), text

        yaml_block = text[3:end]
        body = text[end + 4:].lstrip("\n")

        try:
            fm: dict = yaml.safe_load(yaml_block) or {}
        except yaml.YAMLError:
            logger.warning("Failed to parse frontmatter in %s", note_path)
            fm = {}

        metadata = NoteMetadata(
            title=str(fm.get("title") or note_path.stem),
            date=str(fm["date"]) if fm.get("date") else None,
            description=str(fm["description"]) if fm.get("description") else None,
            tags=list(fm.get("tags") or []),
            aliases=list(fm.get("aliases") or []),
        )
        return metadata, body

    # ------------------------------------------------------------------
    # 2.4  Note resolution
    # ------------------------------------------------------------------

    def resolve_note(self, identifier: str) -> Note:
        """Resolve an identifier to a vault note using three strategies.

        Tries in order:
          1. Relative path from vault root (with or without .md extension)
          2. Filename stem — unique match anywhere in the vault
          3. Alias — scans frontmatter across all vault notes

        Args:
            identifier: A relative path, filename stem, or alias string.

        Returns:
            The matched Note with content and metadata.

        Raises:
            FileNotFoundError: If no note matches (with next-step hint).
            ValueError: If the stem is ambiguous (lists all candidates).
        """
        # 1. Path resolution
        candidate = Path(identifier)
        if not candidate.suffix:
            candidate = candidate.with_suffix(".md")
        full_path = self._root / candidate
        if full_path.exists() and full_path.is_file():
            return self._load_note(full_path)

        # 2. Stem search
        stem = Path(identifier).stem
        matches = [
            p for p in self._root.rglob("*.md")
            if p.stem == stem and not self._is_excluded(p)
        ]
        if len(matches) == 1:
            return self._load_note(matches[0])
        if len(matches) > 1:
            paths = ", ".join(str(p.relative_to(self._root)) for p in sorted(matches))
            raise ValueError(
                f"Multiple notes match '{identifier}'. "
                f"Specify the full path: {paths}. "
                f"Or use search_vault('{identifier}') to see descriptions."
            )

        # 3. Alias scan
        for note_path in sorted(self._root.rglob("*.md")):
            if self._is_excluded(note_path):
                continue
            try:
                metadata, _ = self.parse_frontmatter(note_path)
            except Exception:
                continue
            if identifier in metadata.aliases:
                return self._load_note(note_path)

        raise FileNotFoundError(
            f"No note found with identifier '{identifier}'. "
            "It didn't match any path, filename, or alias. "
            f"Use search_vault('{identifier}') to search by content."
        )

    # ------------------------------------------------------------------
    # 2.5  Folder listing
    # ------------------------------------------------------------------

    def list_folder(
        self, folder: str | None = None
    ) -> list[TopLevelFolder] | list[FolderItem]:
        """List vault folder structure or notes within a specific folder.

        Args:
            folder: Relative folder path from vault root. None returns the
                top-level knowledge folder summary.

        Returns:
            list[TopLevelFolder] when folder is None.
            list[FolderItem] for a specific folder.

        Raises:
            ValueError: If folder is 'inbox' or does not exist.
        """
        if folder is None:
            return self._list_top_level()

        if folder.lower().rstrip("/") == "inbox":
            raise ValueError(
                "The inbox/ folder is a staging area and not browsable. "
                "Use list_folder() to see knowledge folders, "
                "or create_inbox_note() to write to inbox."
            )

        folder_path = self._root / folder
        if not folder_path.exists() or not folder_path.is_dir():
            available = ", ".join(KNOWLEDGE_FOLDERS)
            raise ValueError(
                f"Folder '{folder}' not found. "
                f"Available top-level folders: {available}. "
                "Use list_folder() without arguments to browse."
            )

        items: list[FolderItem] = []
        for md_file in sorted(folder_path.rglob("*.md")):
            if self._is_excluded(md_file):
                continue
            try:
                metadata, _ = self.parse_frontmatter(md_file)
            except Exception:
                metadata = _empty_metadata(md_file.stem)
            items.append(FolderItem(
                path=str(md_file.relative_to(self._root)),
                title=metadata.title,
                description=metadata.description,
            ))
        return items

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _load_note(self, note_path: Path) -> Note:
        metadata, content = self.parse_frontmatter(note_path)
        return Note(
            relative_path=str(note_path.relative_to(self._root)),
            content=content,
            metadata=metadata,
        )

    def _list_top_level(self) -> list[TopLevelFolder]:
        result: list[TopLevelFolder] = []
        for name in KNOWLEDGE_FOLDERS:
            folder_path = self._root / name
            if folder_path.exists() and folder_path.is_dir():
                note_count = sum(
                    1 for p in folder_path.rglob("*.md")
                    if not self._is_excluded(p)
                )
                result.append(TopLevelFolder(name=name, note_count=note_count))
        return result

    def _is_excluded(self, path: Path) -> bool:
        """Return True if path falls under an excluded top-level directory."""
        try:
            rel = path.relative_to(self._root)
        except ValueError:
            return True
        return bool(rel.parts) and rel.parts[0] in EXCLUDED_DIRS


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

# INDEX.md entry pattern: any line containing [[wikilink]]
_WIKILINK_RE = re.compile(r'\[\[([^\]|]+?)(?:\|([^\]]+?))?\]\]')
_AKA_RE = re.compile(r'\(aka ([^)]+)\)')
_TAGS_RE = re.compile(r'_([^_]+)_')
_DESC_RE = re.compile(r'—\s*(.+)$')


def _parse_index_line(line: str) -> IndexEntry | None:
    """Parse one INDEX.md line into an IndexEntry, or None if not a note entry."""
    wikilink_match = _WIKILINK_RE.search(line)
    if not wikilink_match:
        return None

    wikilink = wikilink_match.group(1).strip()
    title = (wikilink_match.group(2) or wikilink).strip()

    aliases: list[str] = []
    aka_match = _AKA_RE.search(line)
    if aka_match:
        aliases = [a.strip() for a in aka_match.group(1).split(",")]

    tags: list[str] = []
    tags_match = _TAGS_RE.search(line)
    if tags_match:
        # Format: "status · tag1, tag2" — split on · and ,
        parts = re.split(r"[·,]", tags_match.group(1))
        tags = [t.strip() for t in parts if t.strip()]

    description = ""
    desc_match = _DESC_RE.search(line)
    if desc_match:
        description = desc_match.group(1).strip()

    return IndexEntry(
        wikilink=wikilink,
        title=title,
        description=description,
        tags=tags,
        aliases=aliases,
    )


def _empty_metadata(stem: str) -> NoteMetadata:
    return NoteMetadata(title=stem, date=None, description=None, tags=[], aliases=[])
