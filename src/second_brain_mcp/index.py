from __future__ import annotations

import re

from second_brain_mcp.models import IndexEntry, SearchResult

_WIKILINK_RE = re.compile(r'\[\[([^\]|]+?)(?:\|([^\]]+?))?\]\]')
_AKA_RE = re.compile(r'\(aka ([^)]+)\)')
_TAGS_RE = re.compile(r'_([^_]+)_')


def parse_index_line(line: str) -> IndexEntry | None:
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

    # Use rfind for the last " — " — avoids false matches on em dashes inside
    # wikilink display titles like "Airflow Status Page — Backend Code Review".
    description = ""
    sep = line.rfind(" — ")
    if sep != -1:
        description = line[sep + 3:].strip()

    return IndexEntry(
        wikilink=wikilink,
        title=title,
        description=description,
        tags=tags,
        aliases=aliases,
    )


def score_index_entry(entry: IndexEntry, query: str) -> int:
    """Return a relevance score for an IndexEntry against a lowercased query.

    Higher score = better match. Returns 0 if no match.
    """
    score = 0
    if query in entry.title.lower():
        score += 4
    for alias in entry.aliases:
        if query in alias.lower():
            score += 3
            break
    for tag in entry.tags:
        if query in tag.lower():
            score += 2
            break
    if query in entry.description.lower():
        score += 1
    return score


def merge_results(
    index_results: list[SearchResult],
    grep_results: list[SearchResult],
) -> list[SearchResult]:
    """Merge INDEX and grep results, deduplicating by path. INDEX results come first."""
    seen: set[str] = set()
    merged: list[SearchResult] = []
    for r in index_results + grep_results:
        if r.path not in seen:
            seen.add(r.path)
            merged.append(r)
    return merged
