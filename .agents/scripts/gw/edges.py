# Mechanism: edge
"""Whether each live edge record and its sidecars keep the edge format's shape.

    uv run --offline --no-project python .agents/scripts/gw/edges.py --check

The shape is the edge format shelf's, `.agents/skills/edge/EDGE-FORMAT.md`: a record's title and
status, its sections and their order, a validator on every invariant, a sidecar for every
extension and a row for every sidecar, and a sidecar's conformance answering every check the
record's `Extending` names. This script rules on form alone. Whether a promise is true, whether an
observation was really made, whether a check is the right one, are judgments it never makes.

A tree with no `docs/edge/` has no records, and that is clean. The script writes nothing; its exit
status is the verdict and its JSON is for the person reading a failure.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

EDGES = "docs/edge"
STATUSES = ("Stub", "Normative", "Normative (tentative)")
SECTIONS = ("Contract", "Invariants", "Extending", "Extensions", "Concerns", "Roadmap")
REQUIRED = ("Contract", "Invariants", "Concerns", "Roadmap")
# An edge things attach to names its checks and its extensions; one without the other is half.
PAIRED = ("Extending", "Extensions")
SIDECAR_SECTIONS = ("Integration", "Conformance")
EXTENSIONS_COLUMNS = ("extension", "standing", "sidecar")
RESULTS = ("observed", "documented", "unobserved", "absent")
UNGUARDED = "⚠ unguarded"
_USAGE = "usage: edges.py --check"
_TITLE = re.compile(r"^# Edge — (\S.*)$")
_SIDECAR_TITLE = re.compile(r"^# (\S.*?) — (\S.*) edge$")
_STATUS = re.compile(r"^- \*\*Status:\*\* (.*)$")
_CHECK = re.compile(r"^\d+\. \*\*([^*]+)\*\* — \S")
_NUMBERED = re.compile(r"^\d+\. ")
_RESULT = re.compile(r"^- \*\*([^*]+)\*\* — (.*)$")
_VALIDATED = re.compile(r"\*validated by:\*\s*(.*)$")
_LIVE = re.compile(r"^live — \*\*([^*]+)\*\*")
_CODE = re.compile(r"`([^`]+)`")
_LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
_DATE = re.compile(r"^observed \d{4}-\d{2}-\d{2}\b")


@dataclass(frozen=True)
class Section:
    title: str
    line: int
    body: list[tuple[int, str]] = field(default_factory=list)


@dataclass(frozen=True)
class Read:
    """One file read into its title line, its `## ` sections, and the lines before the first."""

    record: str
    title: str
    preamble: list[tuple[int, str]]
    sections: list[Section]

    def section(self, name: str) -> Section | None:
        return next((found for found in self.sections if found.title == name), None)

    def as_record(self) -> dict:
        return {"record": self.record, "sections": [found.title for found in self.sections]}


@dataclass(frozen=True)
class Diagnostic:
    record: str
    line: int | None
    problem: str

    def as_record(self) -> dict:
        return {"record": self.record, "line": self.line, "problem": self.problem}


@dataclass(frozen=True)
class Skipped:
    """A file the check could not read. Reported, never dropped: a narrowed scan is not a pass."""

    record: str
    why: str

    def as_record(self) -> dict:
        return {"record": self.record, "why": self.why}


@dataclass(frozen=True)
class Checked:
    records: list[Read]
    diagnostics: list[Diagnostic]
    skipped: list[Skipped]

    def as_record(self) -> dict:
        return {
            "records": [read.as_record() for read in self.records],
            "diagnostics": [note.as_record() for note in self.diagnostics],
            "skipped": [passed_over.as_record() for passed_over in self.skipped],
        }


def main(argv: list[str], root: Path) -> int:
    if argv != ["--check"]:
        print(_USAGE)
        return 2
    checked = check(root)
    print(json.dumps(checked.as_record(), indent=2, ensure_ascii=False))
    return 1 if checked.diagnostics or checked.skipped else 0


def check(root: Path) -> Checked:
    """Every record under `docs/edge/` against the format, and every sidecar against its record."""
    edges = root / EDGES
    records: list[Read] = []
    diagnostics: list[Diagnostic] = []
    skipped: list[Skipped] = []
    if not edges.is_dir():
        return Checked(records, diagnostics, skipped)
    for path in sorted(edges.glob("*.md")):
        read = _read(root, path)
        if isinstance(read, Skipped):
            skipped.append(read)
            continue
        records.append(read)
        diagnostics += _record_problems(root, read)
        diagnostics += _sidecar_problems(root, path, read, skipped)
    for directory in sorted(found for found in edges.iterdir() if found.is_dir()):
        if not (edges / f"{directory.name}.md").is_file():
            name = f"{EDGES}/{directory.name}/"
            diagnostics.append(Diagnostic(name, None, f"sidecars of `{directory.name}`, an edge with no record"))
    return Checked(records, diagnostics, skipped)


# --- reading ------------------------------------------------------------------------------------


def _read(root: Path, path: Path) -> Read | Skipped:
    name = path.relative_to(root).as_posix()
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as error:
        return Skipped(name, str(error))
    title = lines[0] if lines else ""
    preamble: list[tuple[int, str]] = []
    sections: list[Section] = []
    fenced = False
    for number, line in enumerate(lines[1:], start=2):
        if line.startswith("```"):
            fenced = not fenced
        if not fenced and line.startswith("## "):
            sections.append(Section(line[3:].strip(), number))
        elif sections:
            sections[-1].body.append((number, line))
        else:
            preamble.append((number, line))
    return Read(name, title, preamble, sections)


def _checks(read: Read) -> list[str]:
    """The names of the checks the record's `Extending` lists, in its order."""
    extending = read.section("Extending")
    if extending is None:
        return []
    return [found.group(1).strip() for _, line in extending.body if (found := _CHECK.match(line))]


def _bullets(section: Section) -> list[tuple[int, str]]:
    """Top-level bullets, each with its continuation lines joined."""
    joined: list[tuple[int, str]] = []
    for number, line in section.body:
        if line.startswith("- "):
            joined.append((number, line))
        elif joined and line.startswith("  ") and line.strip():
            joined[-1] = (joined[-1][0], f"{joined[-1][1]} {line.strip()}")
    return joined


# --- the record ---------------------------------------------------------------------------------


def _record_problems(root: Path, read: Read) -> list[Diagnostic]:
    problems: list[Diagnostic] = []
    if not _TITLE.match(read.title):
        problems.append(Diagnostic(read.record, 1, "the title is not `# Edge — <Name>`"))
    status = _status(read)
    if status is None:
        problems.append(Diagnostic(read.record, None, "no `- **Status:**` line before the first section"))
    elif status not in STATUSES:
        problems.append(Diagnostic(read.record, None, f"Status `{status}` is not one of {', '.join(STATUSES)}"))
    problems += _section_problems(read)
    problems += _extending_problems(read)
    problems += _invariant_problems(root, read, status)
    return problems


def _extending_problems(read: Read) -> list[Diagnostic]:
    """A numbered line `_checks` cannot read would drop out of every sidecar's count unseen."""
    extending = read.section("Extending")
    if extending is None:
        return []
    return [
        Diagnostic(read.record, number, "a numbered line not in the check form `1. **<check>** — <what it observes>`")
        for number, line in extending.body
        if _NUMBERED.match(line) and not _CHECK.match(line)
    ]


def _status(read: Read) -> str | None:
    for _, line in read.preamble:
        if found := _STATUS.match(line):
            return found.group(1).strip()
    return None


def _section_problems(read: Read) -> list[Diagnostic]:
    problems: list[Diagnostic] = []
    titles = [found.title for found in read.sections]
    for found in read.sections:
        if found.title not in SECTIONS:
            problems.append(Diagnostic(read.record, found.line, f"`## {found.title}` is not a section of the format"))
    for name in REQUIRED:
        if name not in titles:
            problems.append(Diagnostic(read.record, None, f"no `## {name}` section"))
    known = [title for title in titles if title in SECTIONS]
    if known != sorted(known, key=SECTIONS.index):
        problems.append(Diagnostic(read.record, None, f"sections out of order: {', '.join(known)}"))
    present = [name for name in PAIRED if name in titles]
    if len(present) == 1:
        problems.append(Diagnostic(read.record, None, "`## Extending` and `## Extensions` appear together, or neither"))
    return problems


def _invariant_problems(root: Path, read: Read, status: str | None) -> list[Diagnostic]:
    invariants = read.section("Invariants")
    if invariants is None:
        return []
    problems: list[Diagnostic] = []
    checks = _checks(read)
    for number, bullet in _bullets(invariants):
        if UNGUARDED in bullet:
            # A tentative record is held to the same standard; only a Stub may promise unguarded.
            if status is not None and status.startswith("Normative"):
                problems.append(Diagnostic(read.record, number, f"a promise marked unguarded in a {status} record"))
            continue
        validated = _VALIDATED.search(bullet)
        if validated is None:
            problems.append(Diagnostic(read.record, number, "a promise naming no validator and not marked unguarded"))
            continue
        validator = validated.group(1).strip()
        live = _LIVE.match(validator)
        if live:
            if live.group(1).strip() not in checks:
                problems.append(Diagnostic(read.record, number, f"live check `{live.group(1)}` is not a check of `## Extending`"))
            continue
        path = _CODE.match(validator)
        if path is None:
            problems.append(Diagnostic(read.record, number, "a validator neither a backticked path nor `live —` a check"))
        elif not (root / path.group(1)).exists():
            problems.append(Diagnostic(read.record, number, f"validator `{path.group(1)}` does not exist"))
    return problems


# --- the sidecars -------------------------------------------------------------------------------


def _sidecar_problems(root: Path, path: Path, read: Read, skipped: list[Skipped]) -> list[Diagnostic]:
    problems: list[Diagnostic] = []
    named = _named_sidecars(path, read, problems)
    directory = path.with_suffix("")
    present = {found.resolve() for found in directory.glob("*.md")} if directory.is_dir() else set()
    for target, number in named.items():
        if target not in present:
            shown = target.relative_to(root).as_posix() if target.is_relative_to(root) else str(target)
            problems.append(Diagnostic(read.record, number, f"sidecar `{shown}` does not exist"))
    title = _TITLE.match(read.title)
    edge = title.group(1).strip() if title else None
    checks = _checks(read)
    for found in sorted(present):
        if found not in named:
            problems.append(Diagnostic(read.record, None, f"sidecar `{found.relative_to(root).as_posix()}` has no row in `## Extensions`"))
        side = _read(root, found)
        if isinstance(side, Skipped):
            skipped.append(side)
            continue
        problems += _one_sidecar(side, edge, checks)
    return problems


def _named_sidecars(path: Path, read: Read, problems: list[Diagnostic]) -> dict[Path, int]:
    """Each sidecar the `## Extensions` table links, resolved, with the row's line."""
    extensions = read.section("Extensions")
    if extensions is None:
        return {}
    rows = [(number, line) for number, line in extensions.body if line.strip().startswith("|")]
    if not rows:
        return {}
    header = tuple(cell.strip() for cell in rows[0][1].strip().strip("|").split("|"))
    if header != EXTENSIONS_COLUMNS:
        problems.append(Diagnostic(read.record, rows[0][0], f"the Extensions table's columns are not {' | '.join(EXTENSIONS_COLUMNS)}"))
        return {}
    named: dict[Path, int] = {}
    for number, line in rows[2:]:
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        link = _LINK.search(cells[-1]) if cells else None
        if link is None:
            problems.append(Diagnostic(read.record, number, "a row whose sidecar cell links no file"))
            continue
        target = (path.parent / link.group(1)).resolve()
        if target in named:
            problems.append(Diagnostic(read.record, number, f"two rows name the sidecar `{link.group(1)}`"))
        named[target] = number
    return named


def _one_sidecar(side: Read, edge: str | None, checks: list[str]) -> list[Diagnostic]:
    problems: list[Diagnostic] = []
    title = _SIDECAR_TITLE.match(side.title)
    if title is None or (edge is not None and title.group(2).strip() != edge):
        problems.append(Diagnostic(side.record, 1, f"the title is not `# <Extension> — {edge or '<Name>'} edge`"))
    titles = [found.title for found in side.sections]
    if titles != list(SIDECAR_SECTIONS):
        problems.append(Diagnostic(side.record, None, f"sections are {', '.join(titles) or 'none'}, not Integration, Conformance"))
    conformance = side.section("Conformance")
    if conformance is None:
        return problems
    answered: list[str] = []
    for number, bullet in _bullets(conformance):
        found = _RESULT.match(bullet)
        if found is None:
            problems.append(Diagnostic(side.record, number, "a conformance bullet not `- **<check>** — <result>`"))
            continue
        name, result = found.group(1).strip(), found.group(2).strip()
        if name in answered:
            problems.append(Diagnostic(side.record, number, f"check `{name}` answered twice"))
        answered.append(name)
        if name not in checks:
            problems.append(Diagnostic(side.record, number, f"`{name}` is not a check of the record's `## Extending`"))
        word = re.split(r"[\s,;:.]", result, maxsplit=1)[0]
        if word not in RESULTS:
            problems.append(Diagnostic(side.record, number, f"the result opens with `{word}`, not one of {', '.join(RESULTS)}"))
        elif word == "observed" and not _DATE.match(result):
            problems.append(Diagnostic(side.record, number, "an observation without its date, `observed YYYY-MM-DD`"))
    for name in checks:
        if name not in answered:
            problems.append(Diagnostic(side.record, None, f"check `{name}` of the record's `## Extending` has no result"))
    return problems


if __name__ == "__main__":
    # The tree this script sits in; anything that imports it names its tree itself.
    sys.exit(main(sys.argv[1:], Path(__file__).resolve().parents[3]))
