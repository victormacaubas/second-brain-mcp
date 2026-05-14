from __future__ import annotations

import logging
import sys
from functools import lru_cache

from mcp.server.fastmcp import FastMCP

from second_brain_mcp.config import load_config
from second_brain_mcp.models import FolderItem, TopLevelFolder
from second_brain_mcp.vault import Vault

# stdio transport owns stdout — all logging must go to stderr
logging.basicConfig(
    stream=sys.stderr,
    level=logging.WARNING,
    format="%(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)

mcp = FastMCP("second-brain-mcp")


@lru_cache(maxsize=1)
def _get_vault() -> Vault:
    """Process-wide Vault instance; constructed lazily on first tool call."""
    return Vault(load_config())


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
def search_vault(query: str) -> str:
    """Search vault notes by keyword and return ranked matches.

    Use when:
    - The user mentions a topic, concept, or project you need to look up
    - You need to find a note before reading it
    - A broad exploration is needed before diving into a specific note

    Don't use when:
    - You already have a specific note path or stem — use read_note instead
    - The user wants to browse a category — use list_folder instead

    Args:
        query: Keyword or short phrase to search for. Single keywords work
            best (e.g. "airflow", "caching", "chain-of-thought"). The search
            first scans INDEX.md for title/alias/description/tag matches, then
            falls back to full-text grep if INDEX yields fewer than 3 results.
            inbox/ is always excluded.

    Returns:
        Ranked list of up to 20 matching notes (path, title, description,
        tags). If more than 20 match, a count is included. Empty results
        include a suggestion to try broader terms or list_folder.
    """
    try:
        results, total = _get_vault().search(query)
    except Exception as e:
        logger.exception("search_vault failed for query=%r", query)
        return f"Search failed: {e}. Try a different query or use list_folder() to browse."

    if not results:
        return (
            f"No notes found matching '{query}'. "
            "Try broader terms or use list_folder() to browse by category."
        )

    lines: list[str] = []
    cap_note = f" (showing {len(results)} of {total})" if total > len(results) else ""
    lines.append(f"Found {total} result{'s' if total != 1 else ''} for '{query}'{cap_note}:\n")

    for r in results:
        tag_str = ", ".join(r.tags) if r.tags else ""
        tag_part = f" [{tag_str}]" if tag_str else ""
        lines.append(f'- "{r.path}"{tag_part}')
        lines.append(f"  {r.title}")
        if r.description:
            lines.append(f"  {r.description}")

    if total > len(results):
        lines.append(
            f"\nShowing {len(results)} of {total} matches. "
            "Narrow your query for more specific results."
        )

    lines.append("\nUse read_note(identifier=<path>) to open any of these notes.")
    return "\n".join(lines)


@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
def read_note(identifier: str) -> str:
    """Read a vault note by path, filename stem, or alias.

    Returns the full markdown content and frontmatter metadata (title, date,
    description, tags, aliases).

    Use when:
    - You have a specific note to read — from search_vault results, a
      user-named note, or a known path
    - Reading the content of a note the user referenced by name or topic

    Don't use when:
    - You don't know which note to read — use search_vault first
    - You want to browse a folder — use list_folder instead

    Args:
        identifier: One of:
            - Relative path from vault root, e.g.
              "Concepts/mcp-and-agent-fundamentals.md"
            - Filename stem (no extension), e.g.
              "mcp-and-agent-fundamentals"
            - Alias from the note's frontmatter aliases list, e.g.
              "MCP and Agents Learning Notes"
            Paths are tried first, then stem search, then alias scan.

    Returns:
        Note metadata header followed by the full markdown body. On error,
        returns a message with suggestions for what to try next.
    """
    try:
        note = _get_vault().resolve_note(identifier)
    except (FileNotFoundError, ValueError) as e:
        return str(e)
    except Exception as e:
        logger.exception("read_note failed for identifier=%r", identifier)
        return f"Failed to read note '{identifier}': {e}. Use search_vault('{identifier}') to find it."

    meta = note.metadata
    lines: list[str] = [f"title: {meta.title}", f"path: {note.relative_path}"]
    if meta.date:
        lines.append(f"date: {meta.date}")
    if meta.description:
        lines.append(f"description: {meta.description}")
    if meta.tags:
        lines.append(f"tags: {', '.join(meta.tags)}")
    if meta.aliases:
        lines.append(f"aliases: {', '.join(meta.aliases)}")

    parent = note.relative_path.rsplit("/", 1)[0] if "/" in note.relative_path else ""
    hint_parts: list[str] = []
    if meta.tags:
        hint_parts.append(f"search_vault(query='{meta.tags[0]}')")
    if parent:
        hint_parts.append(f"list_folder(folder='{parent}')")
    hint = "Use " + " or ".join(hint_parts) + " to find related notes." if hint_parts else ""

    output = "\n".join(lines) + "\n\n---\n\n" + note.content
    if hint:
        output += f"\n\n---\n{hint}"
    return output


@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
def list_folder(folder: str | None = None) -> str:
    """Browse vault folder structure or list notes within a folder.

    Use when:
    - Exploring what folders or notes exist in the vault
    - The user wants to browse a category (e.g. "what Concepts notes do I have?")
    - Orienting before searching or reading

    Don't use when:
    - Looking for a specific note by topic — use search_vault instead
    - You already have a path — use read_note directly

    Args:
        folder: Optional relative folder path from vault root.
            - Omit (or pass null) to see the top-level knowledge folders
              with note counts: Concepts, Guides, Projects, Systems, Topics.
            - Pass a folder name to list notes, e.g. "Concepts",
              "Projects/airflow-status-page-poc".
            - Do NOT pass "inbox" — that folder is a staging area only.

    Returns:
        Top-level folder summary (no arg) or list of notes with title,
        path, and description within the specified folder.
    """
    try:
        items = _get_vault().list_folder(folder)
    except ValueError as e:
        return str(e)
    except Exception as e:
        logger.exception("list_folder failed for folder=%r", folder)
        return f"Failed to list folder: {e}."

    if not items:
        return (
            f"No notes found in '{folder}'. "
            "Use list_folder() without arguments to see top-level folders."
        )

    lines: list[str] = []

    if isinstance(items[0], TopLevelFolder):
        top_items = [i for i in items if isinstance(i, TopLevelFolder)]
        lines.append("Vault folders:\n")
        for f in top_items:
            lines.append(f"- {f.name} ({f.note_count} notes)")
        lines.append(
            "\nUse list_folder(folder=<name>) to browse a folder, "
            "or search_vault(query) to find notes by keyword."
        )
        return "\n".join(lines)

    note_items = [i for i in items if isinstance(i, FolderItem)]
    lines.append(f"{len(note_items)} notes in {folder}/:\n")
    for item in note_items:
        lines.append(f'- "{item.path}" — {item.title}')
        if item.description:
            lines.append(f"  {item.description}")
    lines.append("\nUse read_note(identifier=<path>) to open a note.")
    return "\n".join(lines)


@mcp.tool(
    annotations={
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False,
    }
)
def create_inbox_note(
    title: str,
    content: str,
    prefix: str | None = None,
) -> str:
    """Create a new note in the vault's inbox/ staging folder.

    Use when:
    - The user wants to save content to the vault: articles, meeting notes,
      conversation summaries, ideas, research findings
    - Capturing anything the user says they want to keep or remember

    Don't use when:
    - Reading or searching the vault — use read_note or search_vault
    - Writing to a specific knowledge folder — only inbox/ writes are allowed

    Args:
        title: Human-readable note title, e.g. "React Server Components Deep
            Dive". Converted to kebab-case for the filename. Required.
        content: Markdown body of the note. Do NOT include a frontmatter
            block — it is generated automatically with title, today's date,
            and tags: [inbox].
        prefix: Note type to prepend to the filename. One of:
            - "article" — saved web article or reading note
            - "convo" — conversation or chat transcript
            - "note" — general note or idea
            - "meeting" — meeting notes
            Omit for an unprefixed note. This guides the /process-inbox
            filing step — choose the type that best fits the content.

    Returns:
        Path of the created file. The note lands in inbox/ and must be
        filed by running /process-inbox in Obsidian.
    """
    try:
        path = _get_vault().create_inbox_note(title=title, content=content, prefix=prefix)
    except ValueError as e:
        return str(e)
    except Exception as e:
        logger.exception("create_inbox_note failed for title=%r", title)
        return f"Failed to create note: {e}."

    return (
        f"Created {path}. "
        "Run /process-inbox in Obsidian to file it into the vault."
    )


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
