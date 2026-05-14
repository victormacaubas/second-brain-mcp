from __future__ import annotations

from dataclasses import dataclass


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
    relative_path: str
    content: str
    metadata: NoteMetadata


@dataclass
class FolderItem:
    path: str
    title: str
    description: str | None


@dataclass
class TopLevelFolder:
    name: str
    note_count: int


@dataclass
class SearchResult:
    path: str
    title: str
    description: str
    tags: list[str]
    match_source: str


def empty_metadata(stem: str) -> NoteMetadata:
    return NoteMetadata(title=stem, date=None, description=None, tags=[], aliases=[])
