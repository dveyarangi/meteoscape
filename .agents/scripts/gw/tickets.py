# Mechanism: ticket
"""What each live ticket declares in its header, and whether the record keeps its declared shape.

    uv run --offline --no-project python .agents/scripts/gw/tickets.py --check
    uv run --offline --no-project python .agents/scripts/gw/tickets.py --list

`--list` prints the live tickets as their headers say them, a markdown table in id order: the
ticket by id and slug, its status word, its type, its title, and the question it answers by id and
slug. It is the ticket list, rendered on request and never committed (the user, 2026-10-10); it
judges nothing, so a field a header lacks prints a dash, and a ticket it cannot read is named under
the table and fails the run.

The shape is the ticket format shelf's, `TICKET-FORMAT.md`, under *The record*: the mark of what
the ticket is a record of, the header's fields and their order, the sections a stage admits, the
acceptance boxes, and the pairing of an RFC with the ticket that shares its basename. The queue is
read for its mark alone. The question store is read for one thing: that a
ticket's `Answers` links an entry the ticket owns. This script rules on form alone. Whether a ticket
should have been written, whether its status is true, whether an outcome is any good, are
judgments it records and never makes.

Live rows only: an archived record is matched by name for pairing and opened for nothing. The
script writes nothing; its exit status is the verdict and its JSON is for the person reading a
failure.
"""

from __future__ import annotations

import json
import posixpath
import re
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import questions  # noqa: E402  (path set above)
from docs_corpus import cited_record, citations, corpus, target_of  # noqa: E402  (path set above)

TICKETS = "docs/tickets"
RFCS = "docs/rfc"
QUEUE = "docs/tickets/README.md"
STATUSES = ("Done", "In progress", "Ready", "Partial", "Planned", "Blocked")
TYPES = ("HITL", "AFK")
ORDERED = ("Status", "Type", "Minted", "Plan", "Depends on", "Blocks", "Answers", "Outcome")
REQUIRED = ("Status", "Type", "Minted", "Answers", "Outcome")
# The day the format narrowed to the five named sections, the stage gone (the user, 2026-10-11): a
# ticket minted before it is held to the required sections and the /verify box alone.
# TODO: the older shape goes once no live ticket was minted before it.
FORMAT_MOVED = "2026-10-11"
RETIRED = ("Kind", "Legacy id", "RFC", "Parent PRD", "User stories addressed")
NAMED_SECTIONS = (
    "Parent",
    "What to build",
    "Acceptance criteria",
    "Out of scope",
    "Parent scope addressed",
)
# A ticket's open questions are entries of the store under its `Answers` question, each holding
# its own argument, so a section listing them is a second home (the user, 2026-10-03).
RETIRED_SECTIONS = ("Open issues",)
REQUIRED_SECTIONS = ("What to build", "Acceptance criteria")
# A live ticket and the queue are records of what they intend to become, as the ticket format
# declares; each carries it as the line its title is followed by, read as what the record is a
# record of. The mark has no colon, which tells it from the retired `Kind:` field; `kind` was its
# earlier name.
MARK = "record of"
FORMER_MARK = "kind"
RECORD_KIND = "what it intends to become"
_USAGE = "usage: tickets.py --check | --list"
_NAMED = re.compile(r"^(\d{2}-\d{4}(?:\.\d{4})*|q-\d{4}(?:\.\d{4})*)-(.+)$")
_DASH = "—"
_BULLET = re.compile(r"^- \*\*([^*]+?):\*\* ?(.*)$")
_MARK = re.compile(rf"^- \*\*({MARK}|{FORMER_MARK})\*\* ?(.*)$")
_BARE = re.compile(r"^\*\*([^*]+?):\*\* ?(.*)$")
_CONTINUATION = re.compile(r"^\s+\S")
_STATUS = re.compile(r"^(Done|In progress|Ready|Partial|Planned|Blocked)(?: \(([^()]*)\))?$")
_DONE_DATED = re.compile(r"^\d{4}-\d{2}-\d{2}(?:, .+)?$")
_DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_BOUNDARY = re.compile(r"[.!?]\s+[A-Z`]")
_CHECKBOX = re.compile(r"^- \[[ xX]\] ")
_HEADING = "## "


@dataclass(frozen=True)
class Field:
    """One header bullet, its continuation lines joined, and the line it starts on."""

    name: str
    value: str
    line: int


@dataclass(frozen=True)
class Section:
    """One `## ` section: its title, its heading's line, and its body as (line, text) pairs."""

    title: str
    line: int
    body: list[tuple[int, str]] = field(default_factory=list)


@dataclass(frozen=True)
class Ticket:
    """One live ticket as its header and sections declare it. Nothing here has been judged yet."""

    record: str
    title: str
    mark: Field
    header: list[Field]
    sections: list[Section]
    bullet_form: bool

    @property
    def fields(self) -> dict[str, str]:
        return {found.name: found.value for found in self.header}

    @property
    def minted(self) -> str | None:
        """The day it was minted, `None` where the header says no such day."""
        said = self.fields.get("Minted", "")
        try:
            return date.fromisoformat(said).isoformat() if _DAY.match(said) else None
        except ValueError:
            return None

    # TODO: every ticket is narrowed once none minted before is live.
    @property
    def narrowed(self) -> bool:
        """Whether it is held to the narrowed shape: minted on or after the day the format moved.
        The older shape is temporary, marked for removal above."""
        return self.minted is not None and self.minted >= FORMAT_MOVED

    def as_record(self) -> dict:
        return {
            "record": self.record,
            "minted": self.minted,
            "fields": self.fields,
            "sections": [section.title for section in self.sections],
        }


@dataclass(frozen=True)
class Diagnostic:
    record: str
    line: int | None
    problem: str

    def as_record(self) -> dict:
        return {"record": self.record, "line": self.line, "problem": self.problem}


@dataclass(frozen=True)
class Skipped:
    """A record the check could not read. Reported, never dropped: a narrowed scan is not a pass."""

    record: str
    why: str

    def as_record(self) -> dict:
        return {"record": self.record, "why": self.why}


@dataclass(frozen=True)
class Checked:
    records: list[Ticket]
    diagnostics: list[Diagnostic]
    skipped: list[Skipped]

    def as_record(self) -> dict:
        return {
            "records": [read.as_record() for read in self.records],
            "diagnostics": [note.as_record() for note in self.diagnostics],
            "skipped": [passed_over.as_record() for passed_over in self.skipped],
        }


@dataclass(frozen=True)
class Listing:
    """The ticket list: a row per live ticket read, and every ticket that could not be read."""

    rows: list[str]
    skipped: list[Skipped]

    def as_text(self) -> str:
        table = ["| Ticket | Status | Type | Title | Question |", "|---|---|---|---|---|", *self.rows]
        unread = [f"not read: {passed_over.record} — {passed_over.why}" for passed_over in self.skipped]
        return "\n".join(table + ([""] + unread if unread else []))


def main(argv: list[str], root: Path) -> int:
    if argv == ["--check"]:
        checked = check(root)
        print(json.dumps(checked.as_record(), indent=2))
        return 1 if checked.diagnostics or checked.skipped else 0
    if argv == ["--list"]:
        listed = listing(root)
        print(listed.as_text())
        return 1 if listed.skipped else 0
    print(_USAGE)
    return 2


def check(root: Path) -> Checked:
    """Every live ticket against the shape, and every RFC against the ticket it is paired with."""
    names = corpus(root)
    entries = {read.record: read for read in questions.read_store(root).index.values()}
    records: list[Ticket] = []
    diagnostics: list[Diagnostic] = []
    skipped: list[Skipped] = []
    for name in live_tickets(names):
        read = _read(root, name)
        if isinstance(read, Skipped):
            skipped.append(read)
            continue
        records.append(read)
        diagnostics += _problems(root, read, names) + _answers_problems(root, read, entries)
    diagnostics += _pairing_problems(names) + _queue_problems(root, names)
    return Checked(records, diagnostics, skipped)


def listing(root: Path) -> Listing:
    """Every live ticket as its header says it, in id order — the parent before its children, since
    a name sorts `-` before `.`. Untracked tickets are listed too, so one minted this session is."""
    entries = {read.record: read for read in questions.read_store(root).index.values()}
    rows: list[str] = []
    skipped: list[Skipped] = []
    for name in live_tickets(corpus(root)):
        read = _read(root, name)
        if isinstance(read, Skipped):
            skipped.append(read)
            continue
        rows.append(_row(root, read, entries))
    return Listing(rows, skipped)


# --- a ticket as a row of the list --------------------------------------------------------------


def _row(root: Path, read: Ticket, entries: dict[str, "questions.Entry"]) -> str:
    """What the header says, shown and never judged: a field it lacks prints a dash."""
    fields = read.fields
    cells = (
        _named_link(read.record),
        _status_word(fields.get("Status")),
        fields.get("Type") or _DASH,
        read.title,
        _question(root, read, entries),
    )
    return "| " + " | ".join(cell.replace("|", "\\|") for cell in cells) + " |"


def _named_link(record: str) -> str:
    """A link to a record whose text is its id and slug, read off its basename."""
    basename = posixpath.splitext(posixpath.basename(record))[0]
    named = _NAMED.match(basename)
    return f"[{named.group(1)} {named.group(2)}]({record})" if named else f"[{basename}]({record})"


def _status_word(status: str | None) -> str:
    """The status without its qualifier, which stays in the ticket. A value the grammar does not
    match is shown as written: whether it is right is `--check`'s to say."""
    if not status:
        return _DASH
    word = _STATUS.match(status)
    return word.group(1) if word else status


def _question(root: Path, read: Ticket, entries: dict[str, "questions.Entry"]) -> str:
    """The entry `Answers` links, as a named link; a dash unless it links exactly one entry."""
    written = citations(read.fields.get("Answers", ""))
    if len(written) != 1:
        return _DASH
    entry = entries.get(cited_record(root, read.record, target_of(written[0])) or "")
    return _named_link(entry.record) if entry else _DASH


# --- reading a ticket ---------------------------------------------------------------------------


def live_tickets(names: list[str]) -> list[str]:
    """The records under `docs/tickets/` itself: not the queue, not anything archived."""
    return sorted(
        name
        for name in names
        if posixpath.dirname(name) == TICKETS and name.endswith(".md") and name != QUEUE
    )


def _read(root: Path, name: str) -> Ticket | Skipped:
    try:
        text = (root / name).read_bytes().decode("utf-8")
    except UnicodeDecodeError:
        return Skipped(name, "is not UTF-8, so the record cannot be read")
    lines = text.splitlines()
    if not lines or not lines[0].startswith("# "):
        return Skipped(name, "does not open with a title line, so nothing after it can be placed")
    mark = _mark(lines)
    header, bullet_form, after = _header(lines, mark.line if mark.name else mark.line - 1)
    return Ticket(name, lines[0][2:].strip(), mark, header, _sections(lines, after), bullet_form)


def _mark(lines: list[str]) -> Field:
    """What the record says it is a record of, on the first non-blank line after its title. A
    record carrying none gets a mark with no name, standing on the line the mark belongs on."""
    at = 1
    while at < len(lines) and not lines[at].strip():
        at += 1
    carried = _MARK.match(lines[at]) if at < len(lines) else None
    if not carried:
        return Field("", "", at + 1)
    return Field(carried.group(1), carried.group(2).strip(), at + 1)


def _header(lines: list[str], at: int) -> tuple[list[Field], bool, int]:
    """The bullet list starting at `at`, and where the body starts.

    A bare `**Field:**` line is read too, so the rest of the header can still be judged, but it
    is reported as the form it is: the shape admits the bullet form and nothing else.
    """
    bullet_form = not (at < len(lines) and _BARE.match(lines[at]))
    marker = _BULLET if bullet_form else _BARE
    header: list[Field] = []
    while at < len(lines):
        opened = marker.match(lines[at])
        if opened:
            header.append(Field(opened.group(1).strip(), opened.group(2).strip(), at + 1))
        elif header and _CONTINUATION.match(lines[at]):
            last = header[-1]
            header[-1] = Field(last.name, f"{last.value} {lines[at].strip()}".strip(), last.line)
        else:
            break
        at += 1
    return header, bullet_form, at


def _sections(lines: list[str], start: int) -> list[Section]:
    sections: list[Section] = []
    for number, line in enumerate(lines[start:], start=start + 1):
        if line.startswith(_HEADING):
            sections.append(Section(line[len(_HEADING) :].strip(), number))
        elif sections:
            sections[-1].body.append((number, line))
    return sections


# --- judging its form ---------------------------------------------------------------------------


def _problems(root: Path, read: Ticket, names: list[str]) -> list[Diagnostic]:
    """Everything about one live ticket that the shelf's declared shape contradicts."""
    return (
        _mark_problems(read.record, read.mark, "ticket")
        + _form_problems(read)
        + _field_problems(read)
        + _plan_problems(root, read, names)
        + _link_problems(root, read)
        + _section_problems(read)
    )


def _mark_problems(record: str, mark: Field, called: str) -> list[Diagnostic]:
    """The kind the record carries against the kind its format declares (the user, 2026-10-08):
    carried, the agent editing it meets the kind in context before adding what the kind refuses."""
    expected = f"`- **{MARK}** {RECORD_KIND}`"
    if not mark.name:
        return [Diagnostic(record, mark.line, f"the {called} names no kind: {expected} follows its title")]
    if mark.name == FORMER_MARK:
        return [Diagnostic(record, mark.line, f"the {called} carries its kind as `- **{FORMER_MARK}**`: write {expected}")]
    if mark.value != RECORD_KIND:
        return [Diagnostic(record, mark.line, f"the {called}'s kind is {mark.value}, and a live {called} is {RECORD_KIND}")]
    return []


def _queue_problems(root: Path, names: list[str]) -> list[Diagnostic]:
    """The queue's mark, where the tree has a queue; a tree without one is not this check's to
    report."""
    if QUEUE not in names:
        return []
    try:
        lines = (root / QUEUE).read_bytes().decode("utf-8").splitlines()
    except UnicodeDecodeError:
        return [Diagnostic(QUEUE, None, "is not UTF-8, so its mark cannot be read")]
    return _mark_problems(QUEUE, _mark(lines), "queue")


def _form_problems(read: Ticket) -> list[Diagnostic]:
    if read.bullet_form:
        return []
    first = read.header[0].line if read.header else 3
    return [
        Diagnostic(
            read.record,
            first,
            "the header is not a bullet list: `**Status:**` where `- **Status:**` is the form",
        )
    ]


def _field_problems(read: Ticket) -> list[Diagnostic]:
    """Presence, vocabulary, retired fields, the shelf's order and Outcome's place at the end."""
    notes = []
    fields = read.fields
    first = read.header[0].line if read.header else 1
    for name in REQUIRED:
        if name not in fields:
            notes.append(Diagnostic(read.record, first, f"the header has no {name} bullet"))
    for found in read.header:
        if found.name in RETIRED:
            notes.append(
                Diagnostic(
                    read.record,
                    found.line,
                    f"{found.name} is no longer a field; a live record carries none of the older ones",
                )
            )
        elif found.name == "Status":
            notes += _status_problems(read.record, found)
        elif found.name == "Type" and found.value not in TYPES:
            notes.append(
                Diagnostic(read.record, found.line, f"Type is `{found.value}`, not HITL or AFK")
            )
        elif found.name == "Minted" and read.minted is None:
            notes.append(
                Diagnostic(read.record, found.line, f"Minted is `{found.value}`, not a day written YYYY-MM-DD")
            )
        elif found.name == "Outcome" and _BOUNDARY.search(found.value):
            notes.append(Diagnostic(read.record, found.line, "Outcome is more than one sentence"))
    return notes + _order_problems(read)


def _status_problems(record: str, found: Field) -> list[Diagnostic]:
    said = _STATUS.match(found.value)
    if not said:
        return [
            Diagnostic(
                record,
                found.line,
                f"Status is `{found.value}`, not one of {', '.join(STATUSES)} "
                "with at most one parenthetical",
            )
        ]
    if said.group(1) == "Done" and not (said.group(2) and _DONE_DATED.match(said.group(2))):
        return [
            Diagnostic(
                record,
                found.line,
                "Done carries its date: the parenthetical opens with YYYY-MM-DD, words may follow "
                "after a comma",
            )
        ]
    return []


def _order_problems(read: Ticket) -> list[Diagnostic]:
    """Outcome last; the known fields in the shelf's order; a one-off field anywhere before it."""
    outcome = next((found for found in read.header if found.name == "Outcome"), None)
    if outcome is not None and read.header[-1] is not outcome:
        follower = read.header[read.header.index(outcome) + 1]
        return [
            Diagnostic(
                read.record, outcome.line, f"Outcome is not the last bullet; {follower.name} follows it"
            )
        ]
    known = [found for found in read.header if found.name in ORDERED and found.name != "Outcome"]
    for earlier, later in zip(known, known[1:]):
        if ORDERED.index(earlier.name) > ORDERED.index(later.name):
            return [
                Diagnostic(
                    read.record,
                    earlier.line,
                    f"{earlier.name} sits before {later.name}; the shelf's order is "
                    + ", ".join(ORDERED),
                )
            ]
    return []


def _plan_problems(root: Path, read: Ticket, names: list[str]) -> list[Diagnostic]:
    """A Plan bullet exactly when an RFC with the basename exists, and pointing at that RFC."""
    basename = posixpath.basename(read.record)
    rfc = next(
        (
            candidate
            for candidate in (f"{RFCS}/{basename}", f"{RFCS}/done/{basename}")
            if candidate in names
        ),
        None,
    )
    plan = next((found for found in read.header if found.name == "Plan"), None)
    first = read.header[0].line if read.header else 1
    if rfc and plan is None:
        return [Diagnostic(read.record, first, f"an RFC exists at {rfc} and the header has no Plan bullet")]
    if plan is not None and rfc is None:
        return [
            Diagnostic(
                read.record,
                plan.line,
                f"the header has a Plan bullet and no RFC named {basename} exists under {RFCS}/",
            )
        ]
    if plan is None:
        return []
    cited = citations(plan.value)
    aimed = cited_record(root, read.record, target_of(cited[0])) if cited else None
    if aimed != rfc:
        return [
            Diagnostic(
                read.record, plan.line, f"Plan links {aimed or plan.value}, not the RFC at {rfc}"
            )
        ]
    return []


def _link_problems(root: Path, read: Ticket) -> list[Diagnostic]:
    """Every citation in a header bullet other than Plan resolves to a file in this tree."""
    notes = []
    for found in read.header:
        if found.name == "Plan":
            continue
        for written in citations(found.value):
            target = target_of(written)
            if target.elsewhere:
                continue
            aimed = cited_record(root, read.record, target)
            if aimed is None or not (root / aimed).exists():
                notes.append(
                    Diagnostic(
                        read.record, found.line, f"{found.name} links {written}, which does not resolve"
                    )
                )
    return notes


def _answers_problems(root: Path, read: Ticket, entries: dict[str, "questions.Entry"]) -> list[Diagnostic]:
    """`Answers` links one entry of the store, and that entry's owner is this ticket — the question
    the ticket's goal answers, which its open questions sit under (the user, 2026-10-03). A
    missing field is the required fields' to report, and a link that resolves nowhere the links'."""
    answers = next((found for found in read.header if found.name == "Answers"), None)
    if answers is None:
        return []
    written = citations(answers.value)
    if len(written) != 1:
        return [Diagnostic(read.record, answers.line, "Answers names one entry of the store by one link")]
    aimed = cited_record(root, read.record, target_of(written[0]))
    if aimed is None or not (root / aimed).exists():
        return []
    entry = entries.get(aimed)
    if entry is None:
        return [Diagnostic(read.record, answers.line, f"Answers links {written[0]}, which is not an entry of the store")]
    owner = entry.parts.get("owner")
    owned = citations(owner.value) if owner else []
    if not owned or cited_record(root, entry.record, target_of(owned[0])) != read.record:
        return [
            Diagnostic(read.record, answers.line, f"Answers links {entry.identity}, whose owner is not this ticket")
        ]
    return []


def _titled(section: Section, name: str) -> bool:
    """Whether a section is the named one — exactly, or with the shelf's provisional suffix."""
    return section.title == name or section.title.startswith(f"{name} ")


def _section_problems(read: Ticket) -> list[Diagnostic]:
    """The required sections; for a narrowed ticket, nothing beyond the five named; the boxes."""
    notes = []
    last_line = read.header[-1].line if read.header else 1
    for name in REQUIRED_SECTIONS:
        if not any(_titled(section, name) for section in read.sections):
            notes.append(Diagnostic(read.record, last_line, f"no {name} section"))
    for section in read.sections:
        if any(_titled(section, name) for name in RETIRED_SECTIONS):
            notes.append(
                Diagnostic(
                    read.record,
                    section.line,
                    f"`{section.title}` is retired: a ticket's open questions are entries of the store "
                    "under its Answers question, drawn by `questions.py --tree`",
                )
            )
    if read.narrowed:
        for extra in read.sections:
            if not any(_titled(extra, name) for name in NAMED_SECTIONS + RETIRED_SECTIONS):
                notes.append(
                    Diagnostic(
                        read.record,
                        extra.line,
                        f"`{extra.title}` is outside the five sections a ticket holds; a decision lands "
                        "where it is made, and the story goes to evidence or a session record",
                    )
                )
    criteria = next(
        (section for section in read.sections if _titled(section, "Acceptance criteria")), None
    )
    if criteria is not None:
        notes += _criteria_problems(read, criteria)
    return notes


def _criteria_problems(read: Ticket, criteria: Section) -> list[Diagnostic]:
    """One box names /verify in every ticket; a narrowed ticket's boxes are all the section holds."""
    notes = []
    boxes = [text for _, text in criteria.body if _CHECKBOX.match(text)]
    if not any("/verify" in text for text in boxes):
        notes.append(Diagnostic(read.record, criteria.line, "no acceptance box names /verify"))
    if read.narrowed:
        for number, text in criteria.body:
            if text.strip() and not _CHECKBOX.match(text) and not _CONTINUATION.match(text):
                notes.append(
                    Diagnostic(
                        read.record,
                        number,
                        f"Acceptance criteria holds a line that is not a checkbox: {text.strip()}",
                    )
                )
    return notes


# --- pairing ------------------------------------------------------------------------------------


def _pairing_problems(names: list[str]) -> list[Diagnostic]:
    """Every RFC names a ticket by basename, and the two sit in the same folder state.

    Names only: a half-closed pair is exactly one file in the wrong folder, and telling that
    needs nothing that is inside either file.
    """
    notes = []
    for rfc in sorted(name for name in names if _is_rfc(name)):
        basename = posixpath.basename(rfc)
        archived = posixpath.dirname(rfc) == f"{RFCS}/done"
        live_ticket = f"{TICKETS}/{basename}" in names
        done_ticket = f"{TICKETS}/done/{basename}" in names
        if not live_ticket and not done_ticket:
            notes.append(
                Diagnostic(rfc, None, f"{rfc} names no ticket: no {basename} under {TICKETS}/ or its done/")
            )
        elif archived and live_ticket and not done_ticket:
            notes.append(
                Diagnostic(
                    rfc, None, f"{rfc} is archived while its ticket is live at {TICKETS}/{basename}"
                )
            )
        elif not archived and done_ticket and not live_ticket:
            notes.append(
                Diagnostic(
                    rfc, None, f"{rfc} is live while its ticket sits in {TICKETS}/done/{basename}"
                )
            )
    return notes


def _is_rfc(name: str) -> bool:
    return posixpath.dirname(name) in (RFCS, f"{RFCS}/done") and name.endswith(".md")


if __name__ == "__main__":
    # The tree this script sits in; anything that imports it names its tree itself.
    sys.exit(main(sys.argv[1:], Path(__file__).resolve().parents[3]))
