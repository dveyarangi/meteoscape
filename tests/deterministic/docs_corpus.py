"""Shared corpus primitives for the documentation guards (docs/cicd.md § CI pipeline).

The two guard modules — integrity and conventions — walk the same repository universe and read
the same markdown grammar; those primitives live here so the guards stay stories about their own
rules. Everything takes explicit inputs, so synthetic corpora in `tmp_path` run through the exact
functions the live gates run.
"""

from __future__ import annotations

import re
import subprocess
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

EXEMPT_PREFIXES = ("docs/sessions/", "docs/tickets/done/", "docs/rfc/done/", "docs/dreams/")
"""Dated-record directories: kept as written, so their outbound links are nobody's promise."""

_FENCE = re.compile(r"^\s*(```|~~~)")
_INLINE_CODE = re.compile(r"`[^`]*`")
_HEADING = re.compile(r"^#{1,6}\s+(.*)$")
_LINK = re.compile(r'!?\[[^\]]*\]\(([^)\s]+)(?:\s+"[^"]*")?\)')
_SLUG_DROPPED = re.compile(r"[^\w\- ]")


def universe(root: Path) -> list[str]:
    """Every file the gate speaks for: tracked plus untracked-but-unignored, exact case.

    Exact-case names from git catch case drift a Windows working tree hides from the Ubuntu CI
    checkout; including untracked files lets a freshly minted document resolve before `git add`.
    """
    listing = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=root,
        capture_output=True,
        encoding="utf-8",
        check=True,
    )
    return [name for name in listing.stdout.split("\0") if name]


def strip_code(text: str) -> str:
    """The prose of a markdown document: fenced blocks and inline code removed.

    Links inside code are illustrations (`./RR-NNNN-slug.md` and friends), not citations.
    """
    prose: list[str] = []
    in_fence = False
    for line in text.splitlines():
        if _FENCE.match(line):
            in_fence = not in_fence
            continue
        if not in_fence:
            prose.append(_INLINE_CODE.sub("", line))
    return "\n".join(prose)


def links(text: str) -> list[str]:
    """Inline link targets in the document's prose."""
    return _LINK.findall(strip_code(text))


def heading_anchors(text: str) -> set[str]:
    """GitHub-style anchor slugs for every heading outside fenced code."""
    anchors: set[str] = set()
    seen: Counter[str] = Counter()
    in_fence = False
    for line in text.splitlines():
        if _FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        heading = _HEADING.match(line)
        if heading is None:
            continue
        slug = _slugify(heading.group(1))
        repeat = seen[slug]
        seen[slug] += 1
        anchors.add(slug if repeat == 0 else f"{slug}-{repeat}")
    return anchors


def _slugify(heading: str) -> str:
    plain = re.sub(r"[*_`]", "", heading.strip().lower())
    return _SLUG_DROPPED.sub("", plain).replace(" ", "-")


def live(name: str) -> bool:
    """A maintained markdown document — one whose outbound links are a kept promise.

    A `README.md` inside a dated-record directory is maintained and counts as live.
    """
    if not name.endswith(".md"):
        return False
    if name.startswith(EXEMPT_PREFIXES):
        return name.rsplit("/", 1)[-1] == "README.md"
    return True


def resolve_name(source: str, relpath: str) -> str:
    """A relative link target as a repo-root name, `..`/`.` folded without touching the filesystem."""
    parts = source.split("/")[:-1]
    for segment in relpath.split("/"):
        if segment == "..":
            if parts:
                parts.pop()
        elif segment not in ("", "."):
            parts.append(segment)
    return "/".join(parts)
