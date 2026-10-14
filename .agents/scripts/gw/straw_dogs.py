# Mechanism: maintain
"""The straw dogs — provisional text bound to the question whose answer will rewrite it — and the
one edit that retires one.

    uv run --offline --no-project python .agents/scripts/gw/straw_dogs.py PATH [PATH ...]
    uv run --offline --no-project python .agents/scripts/gw/straw_dogs.py --guess PATH [PATH ...]
    uv run --offline --no-project python .agents/scripts/gw/straw_dogs.py \
        --remove FILE:LINE --expect sha256:...

Reading a scope reports every operative `<straw-dog>` block in it — and, in code, every `TODO`
naming its question — as JSON, with the question it is bound to, whether it is due, and a
diagnostic for anything a maintainer must look at. Guessing reports where a straw dog probably
stands unwrapped, from the words a sentence carries; a guess is for a person to judge and never
fails the run. Removing takes out one block a maintainer has already judged obsolete.

Whether a straw dog is due is the question store's to say; how its text is rewritten is
`/maintain`'s judgement. The entry contract owns the syntax.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from dataclasses import dataclass, replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import questions  # noqa: E402  (path set just above)
from docs_corpus import (  # noqa: E402  (path set just above)
    ATTRIBUTE,
    INSTALLED_CLOSING,
    INSTALLED_OPENING,
    TODO_QUESTION,
    without_code,
)

TAG = re.compile(r"<straw-dog\b[^<>]*>|</straw-dog\s*>|<straw-dog\b|</straw-dog\b", re.S)
# The tag was `<temporary>` until 2026-09-08. One written from habit would be no straw dog at all —
# the defect this tool exists to end, produced by its own rename — so the old name is a diagnostic.
_RETIRED = re.compile(r"</?temporary\b")
_USAGE = "usage: straw_dogs.py PATH [PATH ...] | --guess PATH [PATH ...] | --remove FILE:LINE --expect HASH"

# In code the marking is a comment line beginning with TODO; one naming its question is a straw
# dog, one naming none is a guess. A sentence merely mentioning the word is neither.
_TODO = re.compile(r"^\s*#\s*TODO\b")
# How a straw dog was bound before it bound to a question: a ticket's path, and on a tag a
# condition beside it. Read so the listing can say what to write instead, and so the install can
# shear one a tree still holds.
TICKET_PATH = re.compile(r"docs/tickets/[\w./-]+\.md")
_OLD_ATTRIBUTE = re.compile(r'\b(until|ticket)\s*=\s*"([^"]*)"', re.S)
# The record folders the harness itself imposes: provisional by status, or history, never a
# surface read as truth, so never guessed over. A project's own folders are its own to judge.
_WORKING_RECORDS = ("docs/tickets/", "docs/rfc/", "docs/spec/", "docs/sessions/")
# The tells. Small on purpose: every sentence the demonstration rested on carried one of these,
# and anything cleverer would be guessing about guessing.
_TELLS = re.compile(
    r"\b(until|for now|does not exist yet|no (?:[\w-]+ ){1,3}exists|by hand|once (?:[\w-]+ ){1,3}lands"
    r"|interim|placeholder|nothing (?:installs|reads|runs))\b",
    re.I,
)


class Refused(Exception):
    """A removal that must not happen. Nothing was written; the reason says what to settle first."""


@dataclass(frozen=True)
class StrawDog:
    """One operative straw dog, as written, and whether the question it waits on has said it is due.

    `question` is the id it is bound to; `until` and `ticket` are an old binding's words, kept so
    the listing can say what replaces them. `fingerprint` covers the whole file's bytes, so a
    removal can prove it is acting on the reading it was shown.
    """

    path: str
    opens: int
    closes: int
    question: str | None
    until: str | None
    ticket: str | None
    depth: int
    contains: int
    fingerprint: str
    span: tuple[int, int]
    due: bool = False

    def as_record(self) -> dict:
        return {
            "path": self.path,
            "opens": self.opens,
            "closes": self.closes,
            "question": self.question,
            "due": self.due,
            "depth": self.depth,
            "contains": self.contains,
            "fingerprint": self.fingerprint,
        }


@dataclass(frozen=True)
class Diagnostic:
    """Something in the scope a maintainer has to resolve before the scope can be called clean."""

    path: str
    line: int
    problem: str

    def as_record(self) -> dict:
        return {"path": self.path, "line": self.line, "problem": self.problem}


@dataclass(frozen=True)
class Surveyed:
    """What one reading of a declared scope found. Empty statements and no diagnostics is a result."""

    scanned: list[str]
    statements: list[StrawDog]
    diagnostics: list[Diagnostic]

    def as_record(self) -> dict:
        return {
            "scanned": self.scanned,
            "statements": [statement.as_record() for statement in self.statements],
            "diagnostics": [note.as_record() for note in self.diagnostics],
        }


@dataclass(frozen=True)
class Candidate:
    """A sentence that probably serves until something replaces it, and was not wrapped to say so."""

    path: str
    line: int
    word: str
    text: str

    def as_record(self) -> dict:
        return {"path": self.path, "line": self.line, "word": self.word, "text": self.text}


@dataclass(frozen=True)
class Guessed:
    """What one guess over a declared scope turned up. A guess is judged, never acted on."""

    scanned: list[str]
    candidates: list[Candidate]

    def as_record(self) -> dict:
        return {
            "scanned": self.scanned,
            "candidates": [candidate.as_record() for candidate in self.candidates],
        }


def main(argv: list[str], root: Path) -> int:
    if argv[:1] == ["--remove"]:
        return _removal(root, argv[1:])
    if argv[:1] == ["--guess"]:
        return _guessing(root, argv[1:])
    if argv[:1] in (["--help"], ["-h"]):
        print(_USAGE)
        return 0
    if not argv or any(operand.startswith("-") for operand in argv):
        print(_USAGE)
        return 2
    try:
        surveyed = survey(root, argv)
    except Refused as refusal:
        print(f"refused, nothing surveyed: {refusal}")
        return 2
    print(json.dumps(surveyed.as_record(), indent=2))
    return 1 if surveyed.diagnostics else 0


def _guessing(root: Path, argv: list[str]) -> int:
    if not argv or any(operand.startswith("-") for operand in argv):
        print(_USAGE)
        return 2
    try:
        guessed = guess(root, argv)
    except Refused as refusal:
        print(f"refused, nothing guessed: {refusal}")
        return 2
    print(json.dumps(guessed.as_record(), indent=2))
    return 0


def _removal(root: Path, argv: list[str]) -> int:
    if len(argv) != 3 or argv[1] != "--expect":
        print(_USAGE)
        return 2
    where, expected = argv[0], argv[2]
    path, _, line = where.rpartition(":")  # from the final colon, so `D:/…/x.md:3` still parses
    if not path or not line.isdigit():
        print(_USAGE)
        return 2
    try:
        remove_straw_dog(root, path, int(line), expected)
    except Refused as refusal:
        print(f"refused, nothing written: {refusal}")
        return 2
    print(f"removed the straw dog at {path}:{line}")
    return 0


def survey(root: Path, paths: list[str]) -> Surveyed:
    """Every operative straw dog in a declared scope, with what is wrong alongside it."""
    scanned: list[str] = []
    statements: list[Statement] = []
    diagnostics: list[Diagnostic] = []
    for name in _records_in(root, paths):
        scanned.append(name)
        try:
            text = _read(root / name)
        except (OSError, UnicodeDecodeError):
            diagnostics.append(Diagnostic(name, 0, "unreadable"))
            continue
        found, notes = _straw_dogs_in(root, name, text)
        statements += found
        diagnostics += notes
    judged, unbound = _against_the_store(root, statements)
    return Surveyed(scanned, judged, diagnostics + unbound)


def _against_the_store(root: Path, statements: list[StrawDog]) -> tuple[list[StrawDog], list[Diagnostic]]:
    """Each straw dog marked due as its question says, and what the store cannot stand behind: an
    id it does not hold, and one merged or superseded, whose straw dogs follow the successor."""
    if not any(statement.question for statement in statements):
        return statements, []
    index = questions.read_store(root).index
    judged: list[StrawDog] = []
    problems: list[Diagnostic] = []
    for statement in statements:
        read = index.get(statement.question) if statement.question else None
        if statement.question and read is None:
            problems.append(Diagnostic(statement.path, statement.opens, f"unknown question: no entry holds {statement.question}"))
        elif read is not None and read.points_to:
            standing = questions.successor(index, read)
            then = f"rebind to {standing.identity}" if standing else f"{statement.question} was {read.kind}, and no question stands in its place"
            problems.append(Diagnostic(statement.path, statement.opens, then))
        judged.append(replace(statement, due=read is not None and questions.due(root, read)))
    return judged, problems


def guess(root: Path, paths: list[str]) -> Guessed:
    """Every unwrapped sentence in a declared scope that carries a tell, for a person to judge."""
    scanned: list[str] = []
    candidates: list[Candidate] = []
    for name in _records_in(root, paths):
        if name.startswith(_WORKING_RECORDS):
            continue
        scanned.append(name)
        try:
            text = _read(root / name)
        except (OSError, UnicodeDecodeError):
            continue
        candidates += _candidates_in(root, name, text)
    return Guessed(scanned, candidates)


def _candidates_in(root: Path, name: str, text: str) -> list[Candidate]:
    if name.endswith(".py"):
        return [
            Candidate(name, number, "TODO", line.strip())
            for number, line in enumerate(text.splitlines(), start=1)
            if _TODO.search(line) and not TICKET_PATH.search(line) and not TODO_QUESTION.match(line)
        ]
    # What is already wrapped says what it is; what sits in an installed block is not this file's
    # to edit, so a candidate there could not be acted on in place. Both are blanked, positions kept.
    prose = without_code(text)
    wrapped, _ = _tags_in(root, name, text)
    prose = _blanked(prose, [straw_dog.span for straw_dog in wrapped] + _installed_spans(prose))
    candidates = []
    offset = 0
    for number, line in enumerate(prose.splitlines(keepends=True), start=1):
        tell = _TELLS.search(line)
        if tell:
            original = text[offset : offset + len(line)].strip()
            candidates.append(Candidate(name, number, tell.group(1).lower(), original))
        offset += len(line)
    return candidates


def _installed_spans(prose: str) -> list[tuple[int, int]]:
    spans = []
    for opening in INSTALLED_OPENING.finditer(prose):
        close = prose.find(INSTALLED_CLOSING, opening.end())
        spans.append((opening.start(), len(prose) if close == -1 else close + len(INSTALLED_CLOSING)))
    return spans


def _blanked(prose: str, spans: list[tuple[int, int]]) -> str:
    kept = list(prose)
    for start, end in spans:
        for at in range(start, end):
            if kept[at] not in "\r\n":
                kept[at] = " "
    return "".join(kept)


def remove_straw_dog(root: Path, path: str, line: int, expect: str) -> None:
    """Take out the one obsolete statement opening at `path:line`, and nothing else.

    Refuses unless the file still hashes to `expect` and the block holds no nested statement: this
    tool has no way to tell whether a child expired with its parent, and a surviving agreement
    inside an obsolete wrapper must be rehomed before the wrapper can go.
    """
    record = root / path
    if not _inside_repository(root, path):
        raise Refused(f"{path} resolves outside the repository")
    if not record.is_file():
        raise Refused(f"{path} is not a record of this repository")
    if path.endswith(".py"):
        raise Refused("a TODO leaves with the code it marks; this tool removes tags, not lines of code")
    if _fingerprint(record) != expect:
        raise Refused(f"{path} has changed since it was read; scan it again and reselect")
    text = _read(record)
    statements, _ = _straw_dogs_in(root, path, text)
    opening = [statement for statement in statements if statement.opens == line]
    if not opening:
        raise Refused(f"no straw dog opens at {path}:{line}")
    statement = opening[0]
    if statement.contains:
        raise Refused(
            f"{path}:{line} contains {statement.contains} nested statement(s); "
            "dispose of them first, then read the file again"
        )
    start, end = _whole_lines_of(text, statement.span)
    _replace_content(record, text[:start] + text[end:])


def _straw_dogs_in(root: Path, name: str, text: str) -> tuple[list[StrawDog], list[Diagnostic]]:
    """One record's straw dogs: tags in a document, TODOs naming their question in code."""
    if name.endswith(".py"):
        return _todos_in(root, name, text)
    return _tags_in(root, name, text)


def _todos_in(root: Path, name: str, text: str) -> tuple[list[StrawDog], list[Diagnostic]]:
    """A TODO that names its question first is a straw dog bound to it; one that names a ticket's
    path is a straw dog bound the old way."""
    fingerprint = _fingerprint(root / name)
    found = []
    offset = 0
    for number, line in enumerate(text.splitlines(keepends=True), start=1):
        question = TODO_QUESTION.match(line)
        ticket = TICKET_PATH.search(line) if _TODO.search(line) and question is None else None
        if question or ticket:
            found.append(
                StrawDog(
                    path=name,
                    opens=number,
                    closes=number,
                    question=question.group(2) if question else None,
                    until=None,
                    ticket=ticket.group(0) if ticket else None,
                    depth=0,
                    contains=0,
                    fingerprint=fingerprint,
                    span=(offset, offset + len(line)),
                )
            )
        offset += len(line)
    return found, _attribute_problems(found)


def _tags_in(root: Path, name: str, text: str) -> tuple[list[StrawDog], list[Diagnostic]]:
    """Read one document's tags into straw dogs, keeping every tag that does not make sense visible."""
    fingerprint = _fingerprint(root / name)
    prose = without_code(text)
    open_tags: list[tuple[int, re.Match[str]]] = []
    spans: list[tuple[int, int, str]] = []
    diagnostics: list[Diagnostic] = []
    for tag in TAG.finditer(prose):
        written = tag.group(0)
        if not written.endswith(">"):
            diagnostics.append(Diagnostic(name, _line_of(text, tag.start()), "malformed"))
            continue
        if written.startswith("</"):
            if not open_tags:
                diagnostics.append(Diagnostic(name, _line_of(text, tag.start()), "never opened"))
                continue
            _, opened = open_tags.pop()
            spans.append((opened.start(), tag.end(), opened.group(0)))
        else:
            open_tags.append((tag.start(), tag))
    diagnostics += [
        Diagnostic(name, _line_of(text, opened.start()), "never closed") for _, opened in open_tags
    ]
    diagnostics += [
        Diagnostic(name, _line_of(text, old.start()), "retired tag name: <temporary> became <straw-dog>")
        for old in _RETIRED.finditer(prose)
        if not old.group(0).startswith("</")
    ]
    statements = _nested(name, text, fingerprint, sorted(spans))
    return statements, diagnostics + _attribute_problems(statements)


def _nested(
    name: str, text: str, fingerprint: str, spans: list[tuple[int, int, str]]
) -> list[StrawDog]:
    """Turn raw spans into straw dogs that know their depth and how many children they hold."""
    statements = []
    for start, end, written in spans:
        attributes = dict(ATTRIBUTE.findall(written)) | dict(_OLD_ATTRIBUTE.findall(written))
        parents = [other for other in spans if _holds(other, (start, end))]
        children = [other for other in spans if _holds((start, end), other)]
        direct = [child for child in children if not any(_holds(kin, child) for kin in children)]
        statements.append(
            StrawDog(
                path=name,
                opens=_line_of(text, start),
                closes=_line_of(text, end - 1),
                question=attributes.get("question"),
                until=attributes.get("until"),
                ticket=attributes.get("ticket"),
                depth=len(parents),
                contains=len(direct),
                fingerprint=fingerprint,
                span=(start, end),
            )
        )
    return statements


def _holds(outer, inner) -> bool:
    """Whether one span strictly encloses another. Equal spans are the same statement, not nesting."""
    return outer[0] < inner[0] and inner[1] <= outer[1]


def _attribute_problems(statements: list[StrawDog]) -> list[Diagnostic]:
    """A straw dog bound to no question, or bound the old way, is a finding — never a silent pass.
    Whether the store holds the question is the survey's to ask."""
    problems = []
    for statement in statements:
        if statement.until is not None or statement.ticket is not None:
            problems.append(Diagnostic(statement.path, statement.opens, _OLD_BINDING))
        elif statement.question is None:
            problems.append(Diagnostic(statement.path, statement.opens, "unbound: no question=\"q-N\""))
    return problems


# What a tree updated past the change meets in its own straw dogs, and what to write instead.
_OLD_BINDING = (
    "old binding: a straw dog binds to the question whose answer will rewrite its text — "
    "<straw-dog question=\"q-N\">, or in code # TODO q-N — never to a ticket or a condition"
)


def _records_in(root: Path, paths: list[str]) -> list[str]:
    """The markdown records and the code a declared scope covers, in a stable order.

    A path naming nothing is refused rather than contributing no records: a scope the caller
    believes it declared and this tool silently dropped would report as a clean, complete scan.
    """
    found: list[str] = []
    for path in paths:
        selected = root / path
        if selected.is_dir():
            found += [
                record.relative_to(root).as_posix()
                for record in selected.rglob("*")
                if record.suffix in (".md", ".py") and ".git" not in record.relative_to(root).parts
            ]
        elif selected.is_file():
            found.append(selected.relative_to(root).as_posix())
        else:
            raise Refused(f"{path} is not a record or directory of this repository")
    return sorted(set(found))


def _whole_lines_of(text: str, span: tuple[int, int]) -> tuple[int, int]:
    """Widen a block's span to the lines it occupies, when nothing else shares them."""
    start, end = span
    line_start = text.rfind("\n", 0, start) + 1
    line_end = text.find("\n", end)
    line_end = len(text) if line_end == -1 else line_end + 1
    if text[line_start:start].strip() or text[end:line_end].strip():
        return span
    return line_start, line_end


def _line_of(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _fingerprint(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _inside_repository(root: Path, name: str) -> bool:
    try:
        return (root / name).resolve().is_relative_to(root.resolve())
    except OSError:
        return False


def _read(path: Path) -> str:
    with path.open(encoding="utf-8", newline="") as handle:
        return handle.read()


def _replace_content(path: Path, text: str) -> None:
    """Write through a neighbouring temporary file, so a failed write never truncates the original."""
    staging = path.with_name(path.name + ".maintain-tmp")
    with staging.open("w", encoding="utf-8", newline="") as handle:
        handle.write(text)
    staging.replace(path)


if __name__ == "__main__":
    # The tree this script sits in; anything that imports it names its tree itself.
    raise SystemExit(main(sys.argv[1:], Path(__file__).resolve().parents[3]))
