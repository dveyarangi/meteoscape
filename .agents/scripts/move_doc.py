"""Mechanical record mover (docs/cicd.md § CI pipeline).

    uv run python .agents/scripts/move_doc.py SRC DST [SRC DST ...]

Git-moves each markdown record, re-depths the moved files' own links, and rewrites inbound
references in live documents. Historical records are left as written. A paired close — ticket and
RFC — goes in one invocation, so each moved record cites the other's final home.

Judgment stays with the caller: no boxes, no statuses, no prose. The doc-integrity guards are the
proof of a move:

    uv run pytest tests/deterministic/test_docs_integrity_guard.py \\
                  tests/deterministic/test_docs_conventions_guard.py
"""

from __future__ import annotations

import posixpath
import re
import subprocess
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tests" / "deterministic"))

from docs_corpus import live, resolve_name, universe  # noqa: E402  (repo path set just above)

_LINK = re.compile(r'(!?\[[^\]]*\]\()([^)\s]+)((?:\s+"[^"]*")?\))')
_FENCE = re.compile(r"^\s*(```|~~~)")
_CODE_SPAN = re.compile(r"`[^`]*`")
_UNMOVED = ("http://", "https://", "mailto:", "#")

_VERIFY = (
    "uv run pytest tests/deterministic/test_docs_integrity_guard.py "
    "tests/deterministic/test_docs_conventions_guard.py"
)


def main(argv: Sequence[str]) -> int:
    if not argv or len(argv) % 2:
        print(__doc__)
        return 2
    pairs = [
        (argv[i].replace("\\", "/"), argv[i + 1].replace("\\", "/")) for i in range(0, len(argv), 2)
    ]
    names = universe(REPO_ROOT)
    problem = refusal(pairs, names)
    if problem:
        print(f"refused, nothing written: {problem}")
        return 2
    perform(REPO_ROOT, names, pairs, move=_git_move)
    print(f"moved {len(pairs)} record(s); prove it:\n    {_VERIFY}")
    return 0


def refusal(pairs: Sequence[tuple[str, str]], names: Sequence[str]) -> str | None:
    """Why the whole batch must not happen — the mover writes all of it or none of it."""
    members = set(names)
    destinations: set[str] = set()
    for source, destination in pairs:
        if source not in members:
            return f"{source} is not a tracked document"
        if not (source.endswith(".md") and destination.endswith(".md")):
            return f"{source} -> {destination}: only markdown records move"
        if posixpath.isabs(destination) or ":" in destination or ".." in destination.split("/"):
            return f"{destination} leaves the corpus"
        if destination in members or destination in destinations:
            return f"{destination} already exists"
        destinations.add(destination)
    return None


def perform(
    root: Path,
    names: Sequence[str],
    pairs: Sequence[tuple[str, str]],
    move: Callable[[Path, str, str], None],
) -> None:
    """Move every record, then make the corpus's links true again — and touch nothing else."""
    mapping = dict(pairs)
    for source, destination in pairs:
        move(root, source, destination)
    for source, destination in pairs:
        _rewrite(root / destination, redepthed, source, destination, mapping)
    moved = set(mapping)
    for name in names:
        if name not in moved and live(name):
            _rewrite(root / name, with_inbound_rewritten, name, name, mapping)


def redepthed(text: str, source: str, destination: str, mapping: dict[str, str]) -> str:
    """The moved record's own links, re-aimed from its new home at every target's final home."""
    return _transformed(text, lambda target: _retarget(target, source, destination, mapping, True))


def with_inbound_rewritten(text: str, citer: str, _: str, mapping: dict[str, str]) -> str:
    """A live citer's links to any moved record, re-aimed at its final home."""
    return _transformed(text, lambda target: _retarget(target, citer, citer, mapping, False))


def _retarget(
    target: str, resolve_from: str, write_from: str, mapping: dict[str, str], redepth: bool
) -> str | None:
    if target.startswith(_UNMOVED):
        return None
    path, fragment_sep, fragment = target.partition("#")
    resolved = resolve_name(resolve_from, path)
    final = mapping.get(resolved)
    if final is None:
        if not redepth:
            return None
        final = resolved
    relative = posixpath.relpath(final, posixpath.dirname(write_from) or ".")
    if not relative.startswith("."):
        relative = "./" + relative
    return relative + fragment_sep + fragment


def _transformed(text: str, retargeted: Callable[[str], str | None]) -> str:
    """Every prose link retargeted; fenced blocks and inline code are illustrations, untouched."""
    lines: list[str] = []
    in_fence = False
    for line in text.split("\n"):
        if _FENCE.match(line):
            in_fence = not in_fence
        if in_fence or not _LINK.search(line):
            lines.append(line)
            continue
        code_spans = [m.span() for m in _CODE_SPAN.finditer(line)]

        def relinked(m: re.Match[str], spans: list[tuple[int, int]] = code_spans) -> str:
            inside_code = any(start <= m.start(2) < end for start, end in spans)
            target = None if inside_code else retargeted(m.group(2))
            return m.group(0) if target is None else m.group(1) + target + m.group(3)

        lines.append(_LINK.sub(relinked, line))
    return "\n".join(lines)


def _rewrite(
    path: Path,
    transform: Callable[[str, str, str, dict[str, str]], str],
    a: str,
    b: str,
    mapping: dict[str, str],
) -> None:
    text = path.read_text(encoding="utf-8", newline="")
    rewritten = transform(text, a, b, mapping)
    if rewritten != text:
        path.write_text(rewritten, encoding="utf-8", newline="")


def _git_move(root: Path, source: str, destination: str) -> None:
    (root / destination).parent.mkdir(parents=True, exist_ok=True)
    tracked = subprocess.run(
        ["git", "ls-files", "--cached", "-z", "--", source], cwd=root, capture_output=True
    ).stdout
    if tracked:
        subprocess.run(["git", "mv", source, destination], cwd=root, check=True)
    else:  # a record minted this arc, not yet added — git meets it at its new home
        (root / source).rename(root / destination)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
