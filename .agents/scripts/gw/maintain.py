# Mechanism: maintain
"""Which mechanisms are due for a re-check, from marks only a maintenance writes.

    uv run --offline --no-project python .agents/scripts/gw/maintain.py --check
    uv run --offline --no-project python .agents/scripts/gw/maintain.py --mark <mechanism> <level> <outcome>

A record is due when what it depends on moved, and a mechanism has two dependences, so it is
checked at two levels. At `parts` its doc is due when a part it owns moved since its mark — the
rows of its *Install adds, uninstall removes* table, whole files, the doc itself aside; a part it
only relies on is its owner's doc to watch. At `output` its records are due when its own doc,
rules file or skill moved, and its doc and skill when the mechanism shape's did: every
mechanism's doc and skill are the shape's outputs, read against it one mechanism at a time in
that mechanism's own row (the user, 2026-10-11). A due level names the files that moved, so the
re-check reads in the direction the file gives — a shape file against the doc and skill, an own
file against the records. A mark is the fingerprint of what a maintenance checked, written by `--mark` when the
maintenance finishes and by nothing else: no edit to a doc counts as a re-check. It keeps each
file's fingerprint too, so a level falling due names the files that moved, were added or went,
and the re-check reads those (the user, 2026-10-11). Dueness is derived at every look and never
stored. The marks' format is `/maintain`'s, in the format shelf beside its skill,
`MARKS-FORMAT.md`.

`--check` never fails on a due mechanism — being due is the news, not a defect — only on marks it
cannot read or a surface it cannot fingerprint. In a recipient the built-in mechanisms are
maintained where core is made, so the clock covers the recipient's own mechanisms alone.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import inject_rules  # noqa: E402  (path set just above)
from docs_corpus import INSTALLED_OPENING, announced, without_code  # noqa: E402
from mechanisms import Declaration, declarations  # noqa: E402

MARKS = "docs/mechanisms/maintenance.md"
# The mechanism whose outputs every mechanism's doc and skill are.
SHAPE = "mechanism-shape"
EVIDENCE = "EVIDENCE.md"
# TODO: a third dependence — a mechanism's records changed
# enough since its mark — waits for each mechanism to declare where its records live.
LEVELS = ("parts", "output")
NEVER = "never maintained"
DUE = "due"
CURRENT = "current"
WHY_MOVED = {
    "parts": "a part it owns moved since its mark",
    "output": "what governs its records or its instructions moved since its mark",
}
WHY_UNNAMED = "it moved since a mark that named no files"
WHY_BUILT_IN = "a recipient's built-in mechanisms came with core, maintained where core is made"
# How the due pair came out: the record amended to a landed decision, the thing repaired to the
# record, or nothing the record says touched (the user, 2026-10-11).
OUTCOMES = ("amended", "repaired", "nothing to change")
COLUMNS = ("mechanism", "level", "fingerprint", "date", "outcome")
FILE_COLUMNS = ("mechanism", "level", "file", "fingerprint")
_FINGERPRINT = re.compile(r"^[0-9a-f]{64}$")
_USAGE = "usage: maintain.py --check | --mark <mechanism> <level> <outcome>"


class Refused(Exception):
    """A mark that must not be written. The message says what to settle first."""


class Unreadable(Exception):
    """A surface that cannot be fingerprinted. Guessed around, it would read as current."""


@dataclass(frozen=True)
class Mark:
    """One row of the marks: what a maintenance checked one mechanism's level against, and when."""

    mechanism: str
    level: str
    fingerprint: str
    date: str
    outcome: str
    files: dict[str, str] = field(default_factory=dict)
    """Each file it was checked against and that file's fingerprint; none in a mark written before
    a mark kept its files."""

    @property
    def row(self) -> str:
        return f"| {self.mechanism} | {self.level} | {self.fingerprint} | {self.date} | {self.outcome} |"

    @property
    def file_rows(self) -> list[str]:
        return [f"| {self.mechanism} | {self.level} | {name} | {each} |" for name, each in sorted(self.files.items())]

    def as_record(self) -> dict:
        return dict(zip(COLUMNS, (self.mechanism, self.level, self.fingerprint, self.date, self.outcome)))


@dataclass(frozen=True)
class Standing:
    """Where one mechanism stands at one level: due, current, or never maintained, and why; when
    due, the files that moved, were added or went since its mark."""

    mechanism: str
    level: str
    state: str
    why: str | None
    moved: list[str] = field(default_factory=list)
    added: list[str] = field(default_factory=list)
    gone: list[str] = field(default_factory=list)

    def as_record(self) -> dict:
        changed = {"moved": self.moved, "added": self.added, "gone": self.gone}
        return {
            "mechanism": self.mechanism,
            "level": self.level,
            "state": self.state,
            "why": self.why,
            **{name: files for name, files in changed.items() if files},
        }


@dataclass(frozen=True)
class Checked:
    """What one reading of the marks against the declarations found."""

    standings: list[Standing]
    built_in: list[str]
    """In a recipient, the mechanisms it received with core and does not maintain."""
    undeclared: list[Mark]
    """Rows whose mechanism is no longer declared: dropped at the next mark, so reported, never failed."""
    diagnostics: list[str]

    def as_record(self) -> dict:
        return {
            "mechanisms": [standing.as_record() for standing in self.standings],
            "built in": {"why": WHY_BUILT_IN, "mechanisms": self.built_in},
            "undeclared": [held.as_record() for held in self.undeclared],
            "diagnostics": self.diagnostics,
        }


def main(argv: list[str], root: Path, today: date | None = None) -> int:
    if argv == ["--check"]:
        checked = check(root)
        print(json.dumps(checked.as_record(), indent=2))
        return 1 if checked.diagnostics else 0
    if len(argv) == 4 and argv[0] == "--mark":
        report = mark(root, *argv[1:], today or date.today())
        print(json.dumps(report, indent=2))
        return 1 if report.get("refusals") else 0
    print(_USAGE)
    return 2


def check(root: Path) -> Checked:
    """Every clocked mechanism at every level, with why it stands where it does."""
    declared = declarations(root)
    clocked = _clocked(root, declared)
    held_marks, unreadable_marks = _read_marks(root)
    standings, unreadable_surfaces = _standings(root, declared, clocked, held_marks)
    return Checked(
        standings,
        built_in=[one.slug for one in _built_in(root, declared)],
        undeclared=[held for held in held_marks if held.mechanism not in _slugs(clocked)],
        diagnostics=unreadable_marks + unreadable_surfaces,
    )


def mark(root: Path, mechanism: str, level: str, outcome: str, today: date) -> dict:
    """Write the one row saying `mechanism` was maintained at `level` against what it reads now.
    Anything it cannot stand behind is refused before a byte is written."""
    declared = declarations(root)
    held_marks, unreadable = _read_marks(root)
    try:
        if unreadable:
            raise Refused(f"the marks do not read — {unreadable[0]}; repair them before marking over them")
        marked = _markable(root, declared, mechanism, level, outcome)
        texts = _authored_surface(root, _surface(root, declared, marked, level))
    except (Refused, Unreadable) as refusal:
        return {"refusals": [str(refusal)]}
    written = Mark(mechanism, level, _fingerprint(texts), today.isoformat(), outcome, _file_fingerprints(texts))
    _write_marks(root, _kept(held_marks, _clocked(root, declared), written) + [written])
    return {"marked": written.row}


def _kept(held_marks: list[Mark], clocked: list[Declaration], written: Mark) -> list[Mark]:
    """Every row a new mark leaves standing: not the one it replaces, and none for a mechanism no
    longer declared, which is how such a row leaves."""
    return [
        held for held in held_marks
        if held.mechanism in _slugs(clocked) and (held.mechanism, held.level) != (written.mechanism, written.level)
    ]


def _standings(
    root: Path, declared: list[Declaration], clocked: list[Declaration], held_marks: list[Mark]
) -> tuple[list[Standing], list[str]]:
    """Where each clocked mechanism stands at each level, and each surface that could not be read
    — said once, though every mechanism's `rules` shares one."""
    marks = {(held.mechanism, held.level): held for held in held_marks}
    standings: list[Standing] = []
    unreadable: list[str] = []
    for mechanism in clocked:
        for level in LEVELS:
            try:
                texts = _authored_surface(root, _surface(root, declared, mechanism, level))
            except Unreadable as reason:
                unreadable.append(str(reason))
                continue
            standings.append(_standing(mechanism.slug, level, marks.get((mechanism.slug, level)), texts))
    return standings, list(dict.fromkeys(unreadable))


def _slugs(mechanisms: list[Declaration]) -> set[str]:
    return {one.slug for one in mechanisms}


def _markable(root: Path, declared: list[Declaration], mechanism: str, level: str, outcome: str) -> Declaration:
    if level not in LEVELS:
        raise Refused(f"{level} is not a level; a mark is at {' or '.join(LEVELS)}")
    if outcome not in OUTCOMES:
        raise Refused(f"{outcome} is not an outcome; a maintenance ends {' or '.join(OUTCOMES)}")
    if mechanism in _slugs(_built_in(root, declared)):
        raise Refused(f"{mechanism} came with core and is maintained where core is made")
    clocked = {one.slug: one for one in _clocked(root, declared)}
    if mechanism not in clocked:
        raise Refused(f"{mechanism} is not a declared mechanism")
    return clocked[mechanism]


def _standing(mechanism: str, level: str, held: Mark | None, texts: dict[str, str]) -> Standing:
    """The whole surface's fingerprint alone decides current or due, so a mark written before marks
    kept their files reads as it always did; the files kept say what changed."""
    if held is None:
        return Standing(mechanism, level, NEVER, "no mark")
    if held.fingerprint == _fingerprint(texts):
        return Standing(mechanism, level, CURRENT, None)
    if not held.files:
        return Standing(mechanism, level, DUE, WHY_UNNAMED)
    now = _file_fingerprints(texts)
    return Standing(
        mechanism,
        level,
        DUE,
        WHY_MOVED[level],
        moved=sorted(name for name in now.keys() & held.files.keys() if now[name] != held.files[name]),
        added=sorted(now.keys() - held.files.keys()),
        gone=sorted(held.files.keys() - now.keys()),
    )


def _clocked(root: Path, declared: list[Declaration]) -> list[Declaration]:
    """The mechanisms this tree maintains: all of them where core is made, and in a recipient
    none of those under `.agents/`, which came with core."""
    return [] if _received_core(root) else declared


def _built_in(root: Path, declared: list[Declaration]) -> list[Declaration]:
    return declared if _received_core(root) else []


def _received_core(root: Path) -> bool:
    # TODO: recipient-own-mechanisms, unminted,
    # settles where a recipient's own mechanisms live; until then every one a recipient holds is core's.
    return announced(root) is not None


# --- what a level is checked against ----------------------------------------------------------


def _surface(root: Path, declared: list[Declaration], mechanism: Declaration, level: str) -> list[str]:
    """The files a level is checked against: at `parts`, every part the mechanism owns but its
    doc, the record side of that pair; at `output`, what governs its records joined with what
    governs its doc and skill — the mechanism shape's own surface, read here one mechanism at a
    time rather than in a row of the shape's."""
    if level == "parts":
        return sorted(_owned_parts(root, mechanism))
    shape = next((one for one in declared if one.slug == SHAPE), None)
    if shape is None:
        raise Unreadable(f"no {SHAPE} is declared, so what every mechanism's doc is written to has no home to read")
    return sorted({*_governing(root, mechanism), *_governing(root, shape)})


def _governing(root: Path, mechanism: Declaration) -> list[str]:
    """What a mechanism's records are written to: its doc, its rules file and its skill."""
    rules = [mechanism.rules] if mechanism.rules else []
    return [mechanism.doc, *rules, *_skill_files(root, mechanism)]


def _owned_parts(root: Path, mechanism: Declaration) -> list[str]:
    """The files the doc says the mechanism is made of, each a whole file: an owned part is never
    a line in another's file, and a directory would hide what moved inside it."""
    owned = []
    for part in mechanism.parts:
        if part.where == mechanism.doc:
            continue
        if (root / part.where).is_dir():
            raise Unreadable(f"{mechanism.slug}'s part {part.where} is a directory, not a file")
        owned.append(part.where)
    return owned


def _skill_files(root: Path, mechanism: Declaration) -> list[str]:
    """Every file beside the instruction file — its format shelf among them, where a record's
    format is declared. Evidence is story and governs nothing, so an `EVIDENCE.md` a skill still
    carries from before its mechanism was declared is left out, as R2 leaves out evidence."""
    if not mechanism.instruction or not (root / mechanism.instruction).is_file():
        raise Unreadable(f"{mechanism.slug}'s instruction file {mechanism.instruction} does not resolve")
    skill = (root / mechanism.instruction).parent
    return [
        path.relative_to(root).as_posix()
        for path in skill.rglob("*")
        if path.is_file() and path.name != EVIDENCE
    ]


def _authored_surface(root: Path, surface: list[str]) -> dict[str, str]:
    """Each file of a surface as its author wrote it, in the surface's order."""
    return {name: _authored(name, _text(root, name)) for name in surface}


def _fingerprint(texts: dict[str, str]) -> str:
    """What a surface says, independent of the line endings a checkout gives it and of the rules
    other mechanisms installed into it."""
    digest = hashlib.sha256()
    for name, text in texts.items():
        digest.update(name.encode("utf-8") + b"\0" + text.encode("utf-8") + b"\0")
    return digest.hexdigest()


def _file_fingerprints(texts: dict[str, str]) -> dict[str, str]:
    """What each file of a surface says, read as the whole surface's fingerprint reads it."""
    return {name: hashlib.sha256(text.encode("utf-8")).hexdigest() for name, text in texts.items()}


def _text(root: Path, name: str) -> str:
    try:
        return (root / name).read_bytes().decode("utf-8")
    except FileNotFoundError:
        raise Unreadable(f"{name} does not resolve") from None
    except UnicodeDecodeError:
        raise Unreadable(f"{name} is not UTF-8") from None


def _authored(name: str, text: str) -> str:
    """A file as its own author wrote it: LF line endings, and every installed block taken back out
    by the installer's own inverse, so installing or retracting a rule moves nothing. A block is
    policed as injection drift, not as content (R2); one the inverse refuses was edited by hand,
    and `inject_rules.py --check` reports the same block as drift. The installer writes into
    markdown alone, so a script or a test among a mechanism's parts is read as written: the tag in
    its text is its own words."""
    text = text.replace("\r\n", "\n")
    if not name.endswith(".md"):
        return text
    for slug in dict.fromkeys(INSTALLED_OPENING.findall(without_code(text))):
        try:
            found = inject_rules.locate(text, slug)
            if found.text is None:
                raise Unreadable(f"{name}: the {slug} block never closes")
            text = inject_rules.without_block(text, found)
        except inject_rules.Refused as refusal:
            raise Unreadable(f"{name}: {refusal}") from None
    return text


# --- the marks --------------------------------------------------------------------------------


def _read_marks(root: Path) -> tuple[list[Mark], list[str]]:
    """The rows as the format in `/maintain`'s skill declares them, and every place one does not
    read. A tree with no marks has none and nothing wrong with it."""
    path = root / MARKS
    if not path.is_file():
        return [], []
    tables = _tables(path.read_text(encoding="utf-8").splitlines())
    if not tables or _cells(tables[0][0][1]) != list(COLUMNS):
        at = tables[0][0][0] if tables else 1
        return [], [f"{MARKS}:{at}: the table's header is not | {' | '.join(COLUMNS)} |"]
    marks: list[Mark] = []
    problems: list[str] = []
    for number, line in tables[0][2:]:
        read, problem = _row(_cells(line), {(held.mechanism, held.level) for held in marks})
        if problem:
            problems.append(f"{MARKS}:{number}: {problem}")
        else:
            marks.append(read)
    if len(tables) > 1:
        problems += _read_files(tables[1], {(held.mechanism, held.level): held for held in marks})
    if len(tables) > 2:
        problems.append(f"{MARKS}:{tables[2][0][0]}: a third table; the marks hold two")
    return marks, problems


def _tables(lines: list[str]) -> list[list[tuple[int, str]]]:
    """Each run of lines opening `|`, with its line numbers: the marks, then the files they kept."""
    tables: list[list[tuple[int, str]]] = []
    for number, line in enumerate(lines, 1):
        if not line.startswith("|"):
            continue
        if tables and tables[-1][-1][0] == number - 1:
            tables[-1].append((number, line))
        else:
            tables.append([(number, line)])
    return tables


def _read_files(table: list[tuple[int, str]], marks: dict[tuple[str, str], Mark]) -> list[str]:
    """Each file a mark kept, filled into that mark; every row that does not read is a problem."""
    if _cells(table[0][1]) != list(FILE_COLUMNS):
        return [f"{MARKS}:{table[0][0]}: the files' header is not | {' | '.join(FILE_COLUMNS)} |"]
    problems: list[str] = []
    for number, line in table[2:]:
        cells = _cells(line)
        if len(cells) != len(FILE_COLUMNS):
            problems.append(f"{MARKS}:{number}: a file row holds {len(cells)} cells, not {len(FILE_COLUMNS)}")
            continue
        mechanism, level, name, fingerprint = cells
        held = marks.get((mechanism, level))
        if held is None:
            problems.append(f"{MARKS}:{number}: a file kept for {mechanism} at {level}, which has no mark")
        elif not _FINGERPRINT.match(fingerprint):
            problems.append(f"{MARKS}:{number}: {fingerprint} is not a fingerprint — 64 lowercase hex")
        elif name in held.files:
            problems.append(f"{MARKS}:{number}: {name} is kept twice for {mechanism} at {level}")
        else:
            held.files[name] = fingerprint
    return problems


def _row(cells: list[str], seen: set[tuple[str, str]]) -> tuple[Mark | None, str | None]:
    if len(cells) != len(COLUMNS):
        return None, f"a row holds {len(cells)} cells, not {len(COLUMNS)}"
    read = Mark(*cells)
    if read.level not in LEVELS:
        return None, f"{read.level} is not a level"
    if not _FINGERPRINT.match(read.fingerprint):
        return None, f"{read.fingerprint} is not a fingerprint — 64 lowercase hex"
    if not _is_date(read.date):
        return None, f"{read.date} is not a date — YYYY-MM-DD"
    if read.outcome not in OUTCOMES:
        return None, f"{read.outcome} is not an outcome"
    if (read.mechanism, read.level) in seen:
        return None, f"a second row for {read.mechanism} at {read.level}"
    return read, None


def _cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _is_date(written: str) -> bool:
    try:
        return date.fromisoformat(written).isoformat() == written
    except ValueError:
        return False


def _write_marks(root: Path, marks: list[Mark]) -> None:
    ordered = sorted(marks, key=lambda held: (held.mechanism, LEVELS.index(held.level)))
    kept = [row for held in ordered for row in held.file_rows]
    text = (
        "# Maintenance marks\n\n"
        "One row per mechanism per level, then each file that level was checked against, written by\n"
        "`maintain.py --mark` when a maintenance finishes; the format is `/maintain`'s, in\n"
        "`.agents/skills/maintain/MARKS-FORMAT.md`.\n\n"
        + _header(COLUMNS)
        + "".join(held.row + "\n" for held in ordered)
        + ("\n" + _header(FILE_COLUMNS) + "".join(row + "\n" for row in kept) if kept else "")
    )
    path = root / MARKS
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def _header(columns: tuple[str, ...]) -> str:
    return "| " + " | ".join(columns) + " |\n" + "|" + "---|" * len(columns) + "\n"


if __name__ == "__main__":
    # The tree this script sits in; anything that imports it names its tree itself.
    sys.exit(main(sys.argv[1:], Path(__file__).resolve().parents[3]))
