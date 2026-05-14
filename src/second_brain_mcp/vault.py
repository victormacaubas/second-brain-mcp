from __future__ import annotations

import logging
import re
import subprocess
from datetime import date
from pathlib import Path

import yaml

from second_brain_mcp.config import Config
from second_brain_mcp.index import merge_results, parse_index_line, score_index_entry
from second_brain_mcp.models import (
    EXCLUDED_DIRS,
    INDEX_FALLBACK_THRESHOLD,
    KNOWLEDGE_FOLDERS,
    MAX_SEARCH_RESULTS,
    VALID_PREFIXES,
    FolderItem,
    IndexEntry,
    Note,
    NoteMetadata,
    SearchResult,
    TopLevelFolder,
    empty_metadata,
)

logger = logging.getLogger(__name__)


class Vault:
    def __init__(self, config: Config) -> None:
        self._root = config.vault_path

    # ------------------------------------------------------------------
    # INDEX.md parser
    # ------------------------------------------------------------------

    def parse_index(self) -> list[IndexEntry]:
        """Read INDEX.md and return all note entries found.

        Re-reads on every call so results stay fresh when the vault changes
        while the server is running.
        """
        index_path = self._root / "INDEX.md"
        if not index_path.exists():
            logger.warning("INDEX.md not found at %s", index_path)
            return []

        entries: list[IndexEntry] = []
        for line in index_path.read_text(encoding="utf-8").splitlines():
            entry = parse_index_line(line)
            if entry:
                entries.append(entry)
        return entries

    # ------------------------------------------------------------------
    # Frontmatter parser
    # ------------------------------------------------------------------

    def parse_frontmatter(self, note_path: Path) -> tuple[NoteMetadata, str]:
        """Split YAML frontmatter from markdown body and return both.

        Args:
            note_path: Absolute path to a vault note.

        Returns:
            Tuple of (metadata, body). Missing frontmatter fields default to
            None / empty list.

        Raises:
            FileNotFoundError: If note_path does not exist.
        """
        text = note_path.read_text(encoding="utf-8")

        if not text.startswith("---"):
            return empty_metadata(note_path.stem), text

        end = text.find("\n---", 3)
        if end == -1:
            return empty_metadata(note_path.stem), text

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
    # Note resolution
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
    # Folder listing
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
                metadata = empty_metadata(md_file.stem)
            items.append(FolderItem(
                path=str(md_file.relative_to(self._root)),
                title=metadata.title,
                description=metadata.description,
            ))
        return items

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(self, query: str) -> tuple[list[SearchResult], int]:
        """Search the vault for notes matching query.

        Runs INDEX-based search first. Falls back to grep if INDEX yields
        fewer than INDEX_FALLBACK_THRESHOLD results. Merges, deduplicates,
        and caps at MAX_SEARCH_RESULTS.

        Args:
            query: Keyword or phrase to search for.

        Returns:
            Tuple of (results, total_found) where total_found may exceed
            len(results) when capped.
        """
        # Build file list once per call — avoids O(N×files) rglob in _search_index.
        file_list = [p for p in self._root.rglob("*.md") if not self._is_excluded(p)]

        index_results = self._search_index(query, file_list)

        if len(index_results) < INDEX_FALLBACK_THRESHOLD:
            grep_results = self._search_grep(query)
            merged = merge_results(index_results, grep_results)
        else:
            merged = index_results

        total = len(merged)
        return merged[:MAX_SEARCH_RESULTS], total

    def _search_index(self, query: str, file_list: list[Path]) -> list[SearchResult]:
        q = query.lower()
        scored: list[tuple[int, IndexEntry]] = []

        for entry in self.parse_index():
            s = score_index_entry(entry, q)
            if s > 0:
                scored.append((s, entry))

        scored.sort(key=lambda x: x[0], reverse=True)

        return [
            SearchResult(
                path=self._resolve_wikilink_path(entry.wikilink, file_list),
                title=entry.title,
                description=entry.description,
                tags=entry.tags,
                match_source="index",
            )
            for _, entry in scored
        ]

    def _search_grep(self, query: str) -> list[SearchResult]:
        exclude_args: list[str] = []
        for d in EXCLUDED_DIRS:
            exclude_args += ["--exclude-dir", d]

        try:
            proc = subprocess.run(
                ["grep", "-r", "-i", "-l", "--include=*.md",
                 "--exclude=INDEX.md", "--exclude=README.md",
                 *exclude_args, query, str(self._root)],
                capture_output=True,
                text=True,
                timeout=10,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            logger.warning("grep fallback failed: %s", e)
            return []

        results: list[SearchResult] = []
        for line in proc.stdout.splitlines():
            abs_path = Path(line.strip())
            if not abs_path.exists():
                continue
            try:
                rel = str(abs_path.relative_to(self._root))
                meta, _ = self.parse_frontmatter(abs_path)
                results.append(SearchResult(
                    path=rel,
                    title=meta.title,
                    description=meta.description or "",
                    tags=meta.tags,
                    match_source="grep",
                ))
            except Exception as e:
                logger.debug("Skipping %s in grep results: %s", abs_path, e)
        return results

    # ------------------------------------------------------------------
    # Inbox write
    # ------------------------------------------------------------------

    def create_inbox_note(
        self,
        title: str,
        content: str,
        prefix: str | None = None,
        *,
        today: str | None = None,
    ) -> str:
        """Write a new note to inbox/ with auto-generated frontmatter.

        Args:
            title: Human-readable title (converted to kebab-case for filename).
            content: Markdown body to write after the frontmatter block.
            prefix: Optional note type — one of article, convo, note, meeting.
            today: ISO date string for the frontmatter date field. Defaults to
                today's date. Accepted as a parameter so tests can pass a
                fixed date without monkey-patching.

        Returns:
            Relative path of the created file (e.g. "inbox/note-my-title.md").

        Raises:
            ValueError: If prefix is not a valid value.
        """
        if prefix is not None and prefix not in VALID_PREFIXES:
            valid = ", ".join(sorted(VALID_PREFIXES))
            raise ValueError(
                f"Invalid prefix '{prefix}'. "
                f"Valid prefixes: {valid}. "
                "Omit prefix for an unprefixed note."
            )

        slug = _to_kebab(title)
        stem = f"{prefix}-{slug}" if prefix else slug
        inbox_dir = self._root / "inbox"
        inbox_dir.mkdir(exist_ok=True)

        target = inbox_dir / f"{stem}.md"
        if target.exists():
            counter = 1
            while (inbox_dir / f"{stem}-{counter}.md").exists():
                counter += 1
            target = inbox_dir / f"{stem}-{counter}.md"

        date_str = today or date.today().isoformat()
        frontmatter = f"---\ntitle: {title}\ndate: {date_str}\ntags:\n  - inbox\n---\n"
        target.write_text(frontmatter + content, encoding="utf-8")

        return str(target.relative_to(self._root))

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
        # Single rglob pass, partitioned by top-level folder name (PERF-02).
        counts: dict[str, int] = {name: 0 for name in KNOWLEDGE_FOLDERS}
        for p in self._root.rglob("*.md"):
            if self._is_excluded(p):
                continue
            rel = p.relative_to(self._root)
            if rel.parts and rel.parts[0] in counts:
                counts[rel.parts[0]] += 1
        return [
            TopLevelFolder(name=name, note_count=counts[name])
            for name in KNOWLEDGE_FOLDERS
            if (self._root / name).is_dir()
        ]

    def _resolve_wikilink_path(
        self, wikilink: str, file_list: list[Path] | None = None
    ) -> str:
        """Convert an INDEX wikilink (stem or path-without-ext) to a relative .md path."""
        if "/" in wikilink:
            return wikilink + ".md"

        candidates = file_list if file_list is not None else [
            p for p in self._root.rglob("*.md") if not self._is_excluded(p)
        ]
        matches = [p for p in candidates if p.stem == wikilink]
        if matches:
            return str(sorted(matches)[0].relative_to(self._root))
        return wikilink + ".md"

    def _is_excluded(self, path: Path) -> bool:
        """Return True if path falls under an excluded top-level directory."""
        try:
            rel = path.relative_to(self._root)
        except ValueError:
            return True
        return bool(rel.parts) and rel.parts[0] in EXCLUDED_DIRS


def _to_kebab(title: str) -> str:
    """Convert a title to a kebab-case filename slug."""
    slug = title.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")
