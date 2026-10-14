# Mechanism: ticket
"""Mechanical record mover — `/ticket`'s paired close, run from `/maintain`'s pass.

    uv run --offline --no-project python .agents/scripts/gw/move_doc.py SRC DST [SRC DST ...]
    uv run --offline --no-project python .agents/scripts/gw/move_doc.py --dry-run SRC DST

Moves each markdown record, re-aims the moved records' own citations from their new homes, and
repairs every citation elsewhere in the repository that pointed at them. A paired close — ticket
and RFC — goes in one invocation, so each moved record cites the other's final home.

Judgment stays with the caller: this script changes no checkbox, status, date or prose, and never
touches the Git index. Eligibility, staging and commit remain `/maintain`'s and the user's. The one
line of a record it does rewrite is its mark: a record landing on a `done/` shelf is a record of
what happened, which follows from the shelf and asks no judgment (the user, 2026-10-10).
"""

from __future__ import annotations

import posixpath
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))

from docs_corpus import (  # noqa: E402  (path set just above)
    citations,
    cited_record,
    corpus,
    target_of,
    with_citations_retargeted,
    without_code,
)

_USAGE = "usage: move_doc.py [--dry-run] SRC DST [SRC DST ...]"
# A live record's kind, and the one an archived record carries; the ticket format declares both.
_LIVE_KIND = "what it intends to become"
_LIVE_MARK = f"- **record of** {_LIVE_KIND}"
_CLOSED_MARK = "- **record of** what happened"
_ARCHIVE = "done"


def main(argv: list[str], root: Path) -> int:
    """Preview or carry out a close, and say enough afterwards for the caller to trust the result."""
    previewing = bool(argv) and argv[0] == "--dry-run"
    operands = argv[1:] if previewing else argv
    if not operands or len(operands) % 2:
        print(_USAGE)
        return 2
    pairs = [(_slashed(operands[at]), _slashed(operands[at + 1])) for at in range(0, len(operands), 2)]

    why = refusal(root, pairs)
    if why:
        print(f"refused, nothing written: {why}")
        return 2
    for mention in unrepaired_mentions(root, pairs):
        print(f"note: {mention} still names a moved record in a form this mover leaves alone")
    if previewing:
        moves, citers = preview(root, pairs)
        for source, destination in moves:
            print(f"would move {source} -> {destination}")
        for citer in citers:
            print(f"would repair citations in {citer}")
        return 0

    try:
        changed = perform(root, pairs, announce=print)
    except CloseInterrupted as interrupted:
        print(interrupted.report())
        return 1
    for dangling in dangling_references(root, changed):
        print(f"note: {dangling} leads nowhere; it is not this close's doing, but it is now visible")
    for problem in unfinished(root, pairs):
        print(f"close incomplete: {problem}")
        return 1
    print(f"closed {len(pairs)} record(s); review and stage the change yourself")
    return 0


def _slashed(operand: str) -> str:
    return operand.replace("\\", "/")


class Interference(OSError):
    """Something else changed the tree between deriving the change set and applying it.

    Whoever made that change may be mid-edit and uncommitted, so it is a failure to report, never
    permission to overwrite.
    """


class CloseInterrupted(Exception):
    """A close that began writing and could not finish. The tree is half-changed, on purpose.

    There is no automatic rollback: the maintainer inspects the actual files and recovers under the
    repair policy, using Git only where the affected content was committed or staged. `completed`,
    `pending` and `failed` are what the recovery starts from — and after an abrupt termination even
    the failed operation has to be checked against the filesystem.
    """

    def __init__(self, failed: str, cause: OSError, completed: list[str], pending: list[str]):
        super().__init__(f"stopped at {failed}: {cause}")
        self.failed = failed
        self.cause = cause
        self.completed = completed
        self.pending = pending

    def report(self) -> str:
        lines = [f"stopped at {self.failed}: {self.cause}", "nothing was rolled back."]
        lines += [f"  completed: {done}" for done in self.completed] or ["  completed: nothing"]
        lines += [f"  pending:   {todo}" for todo in self.pending]
        return "\n".join(lines)


@dataclass(frozen=True)
class _Move:
    """One record leaving its home for another, carrying its own citations re-aimed.

    `before` is the source as the change set read it; `text` is what the destination receives,
    re-aimed and re-marked, so it cannot stand in for the comparison.
    """

    source: str
    destination: str
    before: str
    text: str

    @property
    def subject(self) -> str:
        return self.destination

    def __str__(self) -> str:
        return f"{self.source} -> {self.destination}"

    def announcement(self) -> str:
        return f"moved {self}"

    def apply(self, root: Path) -> None:
        # An edit to the source since it was read would be lost with it.
        if _read(root / self.source) != self.before:
            raise Interference(f"{self.source} changed after the preflight")
        if (root / self.destination).exists():
            raise Interference(f"{self.destination} appeared after the preflight")
        _replace_content(root / self.destination, self.text)
        (root / self.source).unlink()


@dataclass(frozen=True)
class _Repair:
    """One staying record's citations, re-aimed at the homes the moved records now have."""

    name: str
    before: str
    after: str

    @property
    def subject(self) -> str:
        return self.name

    def __str__(self) -> str:
        return f"citations in {self.name}"

    def announcement(self) -> str:
        return f"repaired {self}"

    def apply(self, root: Path) -> None:
        if _read(root / self.name) != self.before:
            raise Interference(f"{self.name} changed after the preflight")
        _replace_content(root / self.name, self.after)


def refusal(root: Path, pairs: list[tuple[str, str]]) -> str | None:
    """Why the whole selection must not happen — the mover writes all of it, or none of it.

    Every check here answers a question the caller cannot answer from the queue alone, and none of
    them touches a byte. A refusal is a maintenance finding, not a partial close.
    """
    records = set(corpus(root))
    sources = [source for source, _ in pairs]
    shape = _malformed(root, records, pairs)
    if shape:
        return shape
    for source, destination in pairs:
        if destination in sources:
            return f"{source} -> {destination}: the destinations overlap another selected record"
    for _, destination in pairs:
        if (root / destination).exists():
            return f"{destination} already exists"
    # Every markdown record, not only the selected ones: a record the scan cannot decode may cite a
    # moved one, and a close that skipped it would report a repair it never attempted.
    for name in _records(root):
        if not _reads_as_utf8(root / name):
            return f"{name} is not UTF-8, so the corpus cannot be read in full"
    return None


def _malformed(root: Path, records: set[str], pairs: list[tuple[str, str]]) -> str | None:
    """Selection defects visible from the names alone, before the tree is consulted further."""
    chosen: list[str] = []
    claimed: set[str] = set()
    for source, destination in pairs:
        for name in (source, destination):
            if not _inside_repository(root, name):
                return f"{name} resolves outside the repository"
            if not name.lower().endswith(".md"):
                return f"{source} -> {destination}: only markdown records move"
        if source not in records:
            return f"{source} is not a record of this repository"
        if source == destination:
            return f"{source} is already there"
        if source in chosen:
            return f"{source} is selected twice"
        if destination.lower() in claimed:
            return f"{destination} is claimed twice"
        chosen.append(source)
        claimed.add(destination.lower())
    return None


def unrepaired_mentions(root: Path, pairs: list[tuple[str, str]]) -> list[str]:
    """Where a moved record is named in a form this mover leaves alone, as `name:line: basename`.

    An HTML `href`, or a bare filename in prose, is a real reference this tool cannot repair. A
    close that said nothing about them would be claiming more repair than it performed.
    """
    wanted = [posixpath.basename(source) for source, _ in pairs]
    mentions: list[str] = []
    for name in _records(root):
        # Blanking the citations first, then the code, leaves exactly the prose that names a record
        # without pointing at it — and leaves it at its original offsets, so the line number is real.
        outside_citations = without_code(
            with_citations_retargeted(_read(root / name), lambda target: " " * len(target))
        )
        for number, line in enumerate(outside_citations.splitlines(), start=1):
            mentions += [f"{name}:{number}: {basename}" for basename in wanted if basename in line]
    return mentions


def unfinished(root: Path, pairs: list[tuple[str, str]]) -> list[str]:
    """What a finished close failed to establish. An empty answer is the postcondition holding."""
    moved = dict(pairs)
    problems = []
    for source, destination in pairs:
        if (root / source).exists():
            problems.append(f"{source} is still at its old home")
        if not (root / destination).exists():
            problems.append(f"{destination} was never created")
        elif _archived(destination) and _mark_line(_read(root / destination)) == _LIVE_MARK:
            problems.append(f"{destination} is archived and still marked {_LIVE_KIND}")
    for name in _records(root):
        for written in citations(_read(root / name)):
            aimed = cited_record(root, name, target_of(written))
            if aimed in moved:
                problems.append(f"{name} still cites {written}")
    return problems


def dangling_references(root: Path, changed: list[str]) -> list[str]:
    """References inside the records this close rewrote that resolve to nothing on disk.

    Usually a defect that predates the close, surfaced because the record was touched. It is
    reported with its owner rather than failing the close or widening it into a whole-tree repair.
    """
    dangling = []
    for name in changed:
        for written in citations(_read(root / name)):
            aimed = cited_record(root, name, target_of(written))
            if aimed and not aimed.startswith("..") and not (root / aimed).exists():
                dangling.append(f"{name} -> {written}")
    return dangling


def preview(root: Path, pairs: list[tuple[str, str]]) -> tuple[list[tuple[str, str]], list[str]]:
    """What a run would do: the moves it would make and the records whose citations would change."""
    planned = _change_set(root, pairs)
    return list(pairs), [step.subject for step in planned if isinstance(step, _Repair)]


def perform(
    root: Path,
    pairs: list[tuple[str, str]],
    announce: Callable[[str], None] | None = None,
) -> list[str]:
    """Move every selected record and make the corpus's citations true again.

    Returns the names of the records whose text changed. The caller has already established
    eligibility; this call assumes `refusal` returned nothing.
    """
    say = announce or (lambda _: None)
    operations = _change_set(root, pairs)
    completed: list[str] = []
    for position, operation in enumerate(operations):
        try:
            operation.apply(root)
        except OSError as failure:
            raise CloseInterrupted(
                operation.subject, failure, completed, [str(rest) for rest in operations[position:]]
            ) from failure
        completed.append(str(operation))
        say(operation.announcement())
    return [operation.subject for operation in operations]


def _change_set(root: Path, pairs: list[tuple[str, str]]) -> list[_Move | _Repair]:
    """Everything the selection implies, derived before a single byte is written.

    Moves come first so that a record's own citations resolve against every final home, and the
    repairs that follow are computed from the same one reading of the tree.
    """
    mapping = dict(pairs)
    moves = []
    for source, destination in pairs:
        before = _read(root / source)
        after = _marked_for(destination, _redepthed(root, before, source, destination, mapping))
        moves.append(_Move(source, destination, before, after))
    citers = []
    for name in _records(root):
        if name in mapping:
            continue
        before = _read(root / name)
        after = _reaimed_throughout(root, before, name, mapping)
        if after != before:
            citers.append(_Repair(name, before, after))
    return [*moves, *citers]


def _marked_for(destination: str, text: str) -> str:
    """The record as its new shelf has it: one landing in a `done/` shelf marked as a record of
    what happened, where it carried the live mark; any other text as it came."""
    if not _archived(destination) or _mark_line(text) != _LIVE_MARK:
        return text
    return text.replace(_LIVE_MARK, _CLOSED_MARK, 1)


def _archived(name: str) -> bool:
    return posixpath.basename(posixpath.dirname(name)) == _ARCHIVE


def _mark_line(text: str) -> str | None:
    """The first non-blank line after the title, where a record carries its mark."""
    lines = [line for line in text.splitlines()[1:] if line.strip()]
    return lines[0] if lines else None


def _records(root: Path) -> list[str]:
    """Every markdown record in the repository — historical ones included, they cite too."""
    return [name for name in corpus(root) if name.lower().endswith(".md")]


def _inside_repository(root: Path, name: str) -> bool:
    """A name that lands under the root even after links and `..` have been followed."""
    try:
        return (root / name).resolve().is_relative_to(root.resolve())
    except OSError:
        return False


def _reads_as_utf8(path: Path) -> bool:
    try:
        _read(path)
    except UnicodeDecodeError:
        return False
    return True


def _redepthed(root: Path, text: str, source: str, destination: str, mapping: dict[str, str]) -> str:
    """The moved record's own references, re-aimed from its new home at every target's final home."""
    return with_citations_retargeted(
        text, lambda written: _reaimed(root, written, source, destination, mapping, redepth=True)
    )


def _reaimed_throughout(root: Path, text: str, citer: str, mapping: dict[str, str]) -> str:
    """A staying record's references to any moved record, re-aimed; everything else as written."""
    return with_citations_retargeted(
        text, lambda written: _reaimed(root, written, citer, citer, mapping, redepth=False)
    )


def _reaimed(
    root: Path,
    written: str,
    resolve_from: str,
    write_from: str,
    mapping: dict[str, str],
    redepth: bool,
) -> str | None:
    target = target_of(written)
    resolved = cited_record(root, resolve_from, target)
    if resolved is None:
        return None
    final = mapping.get(resolved)
    if final is None:
        # An unmoved record keeps its target. Only a relative citation carried by a moving record
        # needs re-aiming at all, and only because its own depth changed.
        if not redepth or target.absolute:
            return None
        final = resolved
    if target.absolute:
        anchor = target.path[: len(target.path) - len(resolved)]
        return target.aimed_at(anchor + final)
    relative = posixpath.relpath(final, posixpath.dirname(write_from) or ".")
    if target.path.startswith("./") and not relative.startswith("."):
        relative = "./" + relative
    return target.aimed_at(relative)


def _read(path: Path) -> str:
    with path.open(encoding="utf-8", newline="") as handle:
        return handle.read()


def _replace_content(path: Path, text: str) -> None:
    """Write through a neighbouring temporary file, so a failed write never truncates the original.

    The failure contract lets a batch stop half-done, but it does not let one record lose content
    the caller may not have committed. `newline=""` keeps the file's own line endings.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    staging = path.with_name(path.name + ".maintain-tmp")
    with staging.open("w", encoding="utf-8", newline="") as handle:
        handle.write(text)
    staging.replace(path)


if __name__ == "__main__":
    # The tree this script sits in; anything that imports it names its tree itself.
    raise SystemExit(main(sys.argv[1:], Path(__file__).resolve().parents[3]))
