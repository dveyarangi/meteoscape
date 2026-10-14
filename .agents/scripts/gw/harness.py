# Mechanism: harness
"""Core reaches a tree that is not its own repository, from a fresh clone of that repository at a ref.

    python .agents/scripts/gw/harness.py <target> --install [--from REPOSITORY] [--at REF]
    python .agents/scripts/gw/harness.py <target> --update [--overwrite] [--from REPOSITORY] [--at REF]
    python .agents/scripts/gw/harness.py <target> --check [--from REPOSITORY]

The source is always the repository, cloned whole and without a checkout into a temporary
directory and read through git, so what a recipient receives is what a commit holds and never a
working tree. What ships is every file under the core directory at the ref plus the entry file and
the host stub, transformed in memory before a byte is written: the origin's own local blocks
removed, every straw-dog wrapper and every TODO's question binding sheared with its content kept, the
entry file's announce line stamped `<repository>@<ref>, <date>`, and the result held to the leak
rule the origin's check applies. That line is the recipient's only revision record; a check clones
the announced ref again and compares. Every refusal writes nothing. A loader link the platform
refuses to create is not a refusal: everything else lands, and the report carries the exact command
for the person. The contract is the architecture's; the decisions are the install spec's.
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True  # a run from inside a recipient leaves nothing beside its scripts

import io  # noqa: E402
import json  # noqa: E402
import os  # noqa: E402
import re  # noqa: E402
import shutil  # noqa: E402
import stat  # noqa: E402
import subprocess  # noqa: E402
import tarfile  # noqa: E402
import tempfile  # noqa: E402
from dataclasses import dataclass, field  # noqa: E402
from datetime import datetime, timezone  # noqa: E402
from pathlib import Path  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))

import inject_rules  # noqa: E402  (path set just above)
import product  # noqa: E402
import questions  # noqa: E402
from docs_corpus import (  # noqa: E402
    ANNOUNCE,
    ENTRY_FILE,
    RETIRED_TAG,
    SCRIPTS,
    TODO_QUESTION,
    UnreadableCode,
    announced,
    corpus,
    docs_mentioned,
    docs_mentioned_in_code,
    without_code,
)
from mechanisms import FRONT_PAGE as INSTALLED_FRONT_PAGE, PAINTED_DOORS, TESTS  # noqa: E402
from straw_dogs import TAG  # noqa: E402

CORE = ".agents/"
HOST_STUB = "CLAUDE.md"
LICENSE = "LICENSE"
INSTALLED_LICENSE = f"{CORE}LICENSE"
LOCAL_FILE = inject_rules.LOCAL_FILE
LINKS = (".claude/skills", ".cursor/skills")
# The interpreter every core hook runs under, one line in the clone's Git directory: per clone by
# construction, so no commit carries a path that is true on one machine only.
INTERPRETER_RECORD = "gw-interpreter"
LINK_TARGET = "../.agents/skills"
SKILLS = ".agents/skills"
HARNESS_SKILL = f"{SKILLS}/harness/SKILL.md"
FRONT_PAGE = "README.md"
QUEUE_ARRIVAL = f"{SKILLS}/ticket/QUEUE-ARRIVAL.md"
DELIVERY_STATUS = "docs/tickets/README.md"
ARRIVAL_STATE = re.compile(r"^```delivery-status[ \t]*\r?\n(?P<said>.*?)^```", re.M | re.S)
REPOSITORY = re.compile(r"^Repository: (?P<url>\S+)[ \t]*(?:\r?\n|\Z)", re.M)
MODES = ("--install", "--update", "--check", "--links")
# Set by the installer that hands an update on, so the incoming ref's own runs it and hands it on
# to nobody.
HANDED_OFF = "GOODWOLF_UPDATE_HANDED_OFF"
_USAGE = (
    "usage: harness.py <target> --install [--replace-clone] [--from REPOSITORY] [--at REF]\n"
    "       harness.py <target> --update [--overwrite] [--from REPOSITORY] [--at REF]\n"
    "       harness.py <target> --check [--from REPOSITORY]\n"
    "       harness.py <target> --links"
)


class Refused(Exception):
    """Something that must not be written past. The message says which step and what to settle."""


@dataclass(frozen=True)
class Ref:
    """One commit of the repository, as the announce line will name it."""

    repository: str
    commit: str
    announced: str
    date: str

    @property
    def stamp(self) -> str:
        return f"Entry contract: {self.repository}@{self.announced}, {self.date}."

    def as_record(self) -> dict:
        return {"repository": self.repository, "commit": self.commit, "announced": self.announced, "date": self.date}


@dataclass
class Report:
    """What one run did, in the order it did it. `arrived` is the gate's verdict and nothing else's."""

    target: str
    mode: str
    repository: str
    ref: dict | None = None
    written: list[str] = field(default_factory=list)
    replaced: list[str] = field(default_factory=list)
    deleted: list[str] = field(default_factory=list)
    own: list[str] = field(default_factory=list)
    links: list[dict] = field(default_factory=list)
    pending: list[str] = field(default_factory=list)
    injected: list[dict] = field(default_factory=list)
    gates: dict = field(default_factory=dict)
    excluded: list[str] = field(default_factory=list)
    links_resolve: dict = field(default_factory=dict)
    interpreter: dict = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
    refusals: list[str] = field(default_factory=list)
    arrived: bool = False

    def as_record(self) -> dict:
        record = dict(self.__dict__)
        if self.mode == "links":
            # No gate ran: a verdict printed false would read as an install that failed.
            for verdict in ("arrived", "gates", "ref"):
                del record[verdict]
        return record


def main(argv: list[str]) -> int:
    parsed = _parsed(argv)
    if parsed is None:
        print(_USAGE)
        return 2
    target, mode, overwrite, replace_clone, repository, ref = parsed
    report = Report(target, mode[2:], repository or "")
    try:
        if mode == "--links":
            link(Path(target), report)
        else:
            if repository is None:
                repository = report.repository = home()
            with Source(repository) as source:
                if mode == "--update" and HANDED_OFF not in os.environ:
                    return _handed_off(source, source.resolve(ref or "HEAD"), target, overwrite)
                if mode == "--update":
                    report.notes.append(
                        f"the update ran {source.resolve(ref or 'HEAD').announced}'s own installer, "
                        f"handed the run by {os.environ[HANDED_OFF]}"
                    )
                run(Path(target), mode, overwrite, source, ref, report, replace_clone)
    except Refused as refusal:
        report.refusals.append(str(refusal))
    print(json.dumps(report.as_record(), indent=2))
    if mode == "--links":
        return 0 if not report.pending and not report.refusals else 1
    return 0 if report.arrived else 1


def _handed_off(source: Source, wanted: Ref, target: str, overwrite: bool) -> int:
    """An update run by the incoming ref's own installer, from that ref's core unpacked beside the
    clone: the tree's installer is as old as its last install and cannot know what a later ref
    brings, while the incoming one reads what an earlier one left. Pinned to the resolved commit,
    so both read one ref; its report is the run's."""
    with tempfile.TemporaryDirectory(prefix="harness-incoming-") as scratch:
        incoming = Path(scratch)
        for path, data in source.files(wanted).items():
            (incoming / path).parent.mkdir(parents=True, exist_ok=True)
            (incoming / path).write_bytes(data)
        script = incoming / SCRIPTS / "harness.py"
        if not script.is_file():
            raise Refused(f"update: {wanted.announced} holds no {SCRIPTS}harness.py to run the update")
        arguments = [target, "--update", "--from", source.repository, "--at", wanted.commit]
        handed = subprocess.run(
            [sys.executable, str(script), *arguments, *(["--overwrite"] if overwrite else [])],
            capture_output=True, encoding="utf-8", errors="replace",
            env={**os.environ, HANDED_OFF: "the tree's installer"},
        )
    print(handed.stdout, end="")
    print(handed.stderr, end="", file=sys.stderr)
    return handed.returncode


def link(target: Path, report: Report) -> None:
    """The per-clone step: a clone of a tree that holds core has no loader links until this makes
    them, from the tree's own copy, with no source and no network. The links are the install's
    link step run alone; a pending one is the same accepted state, and the exit says it is left."""
    target = _work_tree_root(target, source=None)
    if not (target / SKILLS).is_dir():
        raise Refused(f"links: {target} holds no {SKILLS} — --install first")
    plan = _link_plan(target)
    _make_links(target, plan, report)
    _exclude_links(target, plan, report)
    _record_interpreter(target, report)
    report.links_resolve = _links_resolve(target)


def run(
    target: Path, mode: str, overwrite: bool, source: Source, ref: str | None, report: Report,
    replace_clone: bool = False,
) -> None:
    """The sequence: refuse what cannot be satisfied, copy, stamp, link, inject, then the gate.

    Replacing a clone: what a host makes of *install <url> here* in an empty folder is the
    origin cloned into it, and the agent may not delete what it cloned. A clean clone of the
    repository holds nothing of the person's, so it is turned into an install in place — the
    shipment built first, at the clone's own commit, then the tree emptied, a repository begun
    afresh, and the install run as into an empty folder."""
    if mode == "--install":
        _initialise_if_empty(target.resolve(), report)
    target = _work_tree_root(target, source, replace_clone)
    if mode == "--check":
        wanted = _announced_ref(target, source, required=True)
        shipment = Shipment.earlier(source, wanted)
        report.ref = wanted.as_record()
        _gate(target, shipment, report)
        return
    head = _clean_clone_head(target) if replace_clone else "HEAD"
    wanted = source.resolve(ref or head)
    report.ref = wanted.as_record()
    shipment = Shipment.at(source, wanted)
    if mode == "--install":
        if replace_clone:
            _replace_clone(target, report)
        _refuse_unless_empty(target, shipment)
        previous = None
    else:
        previous = _refuse_unless_updatable(target, source, shipment, overwrite, report)
    plan = _link_plan(target)
    wiring = _wiring_plan(target, shipment, previous)
    _refuse_unless_injectable(target, shipment, previous)
    _write(target, shipment, previous, report)
    _write_delivery_status(target, shipment, report)
    _seed_store(target, report)
    _seed_product_document(target, report)
    _write_wiring(target, wiring, report)
    _make_links(target, plan, report)
    _exclude_links(target, plan, report)
    _record_interpreter(target, report)
    _inject(target, report)
    _gate(target, shipment, report)


def _parsed(argv: list[str]) -> tuple[str, str, bool, bool, str | None, str | None] | None:
    """Exactly one target, one mode, and the options each mode admits; anything else is usage.

    An absent `--from` stays absent rather than defaulting here: the default is read from the
    harness skill, and a run that was given a repository must never need a skill to be there.
    """
    words: list[str] = []
    modes: list[str] = []
    overwrite = False
    replace_clone = False
    repository = None
    ref = None
    operands = list(argv)
    while operands:
        operand = operands.pop(0)
        if operand in MODES:
            modes.append(operand)
        elif operand == "--overwrite":
            overwrite = True
        elif operand == "--replace-clone":
            replace_clone = True
        elif operand in ("--from", "--at") and operands:
            value = operands.pop(0)
            if operand == "--from":
                repository = value
            else:
                ref = value
        elif operand.startswith("-"):
            return None
        else:
            words.append(operand)
    if len(words) != 1 or len(modes) != 1:
        return None
    mode = modes[0]
    if overwrite and mode != "--update":
        return None
    if ref is not None and mode == "--check":
        return None
    if mode == "--links" and (repository is not None or ref is not None):
        return None
    if replace_clone and mode != "--install":
        return None
    return words[0], mode, overwrite, replace_clone, repository, ref


# --- the source ------------------------------------------------------------------------------


def home() -> str:
    """Where core comes from, read from the one line that authors it — the harness skill beside
    this script. No constant: the line is the only authored home, so a fork edits it once and
    everything the fork installs names the fork."""
    skill = Path(__file__).resolve().parents[3] / HARNESS_SKILL  # the tree this script sits in
    if not skill.is_file():
        raise Refused(f"source: {HARNESS_SKILL} is not beside this script; name the repository with --from")
    named = REPOSITORY.findall(_read(skill))
    if len(named) != 1:
        found = "no Repository line" if not named else f"{len(named)} Repository lines"
        raise Refused(f"source: {HARNESS_SKILL} holds {found}; name the repository with --from")
    return named[0]


def resolved(repository: str) -> str:
    """What a recipient is told, from what this run was given: a URL verbatim, a path as an
    absolute one, so a recipient installed from a clone on disk holds no path relative to where
    somebody once stood."""
    local = Path(repository)
    return local.resolve().as_posix() if local.exists() else repository


class Source:
    """The repository, cloned whole and without a checkout for one run, read through git only.

    A checkout would let `core.autocrlf` and `core.symlinks` rewrite what ships; reading blobs
    keeps every byte the commit holds. GitHub serves no fetch by a short commit, so the clone is
    whole and any ref — branch, tag, short or full commit — resolves locally.
    """

    def __init__(self, repository: str) -> None:
        self.repository = repository
        self.name = repository_name(repository)
        self._clone: Path | None = None

    def __enter__(self) -> Source:
        self._clone = Path(tempfile.mkdtemp(prefix="harness-")).resolve()
        cloned = subprocess.run(
            ["git", "clone", "--quiet", "--no-checkout", self.repository, str(self._clone)],
            capture_output=True,
            encoding="utf-8",
        )
        if cloned.returncode != 0:
            raise Refused(f"clone: {self.repository} could not be cloned — {cloned.stderr.strip()}")
        return self

    def __exit__(self, *_: object) -> None:
        if self._clone is not None:
            shutil.rmtree(self._clone, onexc=_writable_then_retry)

    def resolve(self, ref: str) -> Ref:
        commit = self._commit(ref)
        if commit is None:
            raise Refused(f"ref: {ref} does not resolve in {self.repository}")
        return Ref(self.name, commit, self._tag(commit) or self._short(commit), self._date(commit))

    def files(self, ref: Ref) -> dict[str, bytes]:
        """Every file under the core directory at the commit, plus the entry file, the host stub,
        the license and the front page, as the commit holds them: nothing else
        travels — not the local file, not `docs/`.

        The license and the front page are the source's root files, placed under the core
        directory because a recipient's root is its own: the license's notice must go with every
        copy, and the front page beside the harness skill is what an installing agent introduces
        the harness from. Each is read apart from the archive, which refuses a path the commit
        lacks — and every ref before the license lacks it."""
        files = self._archived(ref, (CORE.rstrip("/"), ENTRY_FILE, HOST_STUB))
        for root_file, installed in ((LICENSE, INSTALLED_LICENSE), (FRONT_PAGE, INSTALLED_FRONT_PAGE)):
            held = self._blob(ref, root_file)
            if held is not None:
                files[installed] = held
        return files

    # What follows reads the clone, and is all that does: the choices above are made on what it
    # returns, so a source held some other way answers these and inherits the rest.

    def _commit(self, ref: str) -> str | None:
        return self._git("rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")

    def _tag(self, commit: str) -> str | None:
        return self._git("describe", "--tags", "--exact-match", commit)

    def _short(self, commit: str) -> str:
        return self._git("rev-parse", "--short", commit) or commit[:7]

    def _date(self, commit: str) -> str:
        return self._git("log", "-1", "--format=%cs", commit) or ""

    def _archived(self, ref: Ref, paths: tuple[str, ...]) -> dict[str, bytes]:
        """Every file at or under the paths, as the commit holds them. One archive of the ref, one
        process: reading sixty files one `cat-file` at a time cost more than the clone."""
        # `archive` smudges like a checkout would — `core.autocrlf` on Windows turns every line
        # ending — so conversion is switched off for this one command and the bytes are the commit's.
        archived = subprocess.run(
            ["git", "-C", str(self._clone), "-c", "core.autocrlf=false", "-c", "core.eol=lf", "archive",
             "--format=tar", ref.commit, "--", *paths],
            capture_output=True,
        )
        if archived.returncode != 0:
            raise Refused(f"read: {self.repository} at {ref.announced} could not be archived — {archived.stderr.decode(errors='replace').strip()}")
        files: dict[str, bytes] = {}
        with tarfile.open(fileobj=io.BytesIO(archived.stdout)) as archive:
            for member in archive.getmembers():
                if member.isfile():
                    files[member.name] = archive.extractfile(member).read()
        return files

    def _blob(self, ref: Ref, path: str) -> bytes | None:
        """A file's bytes as the commit holds them — a blob is never smudged — or None when the
        commit has no such file."""
        read = subprocess.run(
            ["git", "-C", str(self._clone), "cat-file", "blob", f"{ref.commit}:{path}"], capture_output=True
        )
        return read.stdout if read.returncode == 0 else None

    def _git(self, *arguments: str) -> str | None:
        done = subprocess.run(
            ["git", "-C", str(self._clone), *arguments], capture_output=True, encoding="utf-8"
        )
        return done.stdout.strip() if done.returncode == 0 else None


def repository_name(repository: str) -> str:
    """The last segment of a URL or path, without `.git`: what the announce line calls it."""
    trimmed = repository.replace("\\", "/").rstrip("/")
    name = trimmed.rsplit("/", 1)[-1]
    return name[:-4] if name.endswith(".git") else name


def _writable_then_retry(function, path, _excinfo) -> None:
    # Git leaves its objects read-only; on Windows that alone makes `rmtree` fail.
    os.chmod(path, stat.S_IWRITE)
    function(path)


# --- what ships ------------------------------------------------------------------------------


@dataclass(frozen=True)
class Shipment:
    """The manifest at one ref, transformed — and, when it is about to ship, held to the leak rule —
    before anything is written."""

    ref: Ref
    files: dict[str, str]
    arrival: str

    @classmethod
    def at(cls, source: Source, ref: Ref) -> Shipment:
        files = _transformed(source, ref, held=True)
        if HARNESS_SKILL not in files:
            raise Refused(f"ship: {ref.announced} has no {HARNESS_SKILL}; this is not the harness")
        _refuse_unless_the_roots_are_said(files, ref)
        _refuse_unless_the_product_document_is_said(files, ref)
        return cls(ref, files, arrival_state(files, ref))

    @classmethod
    def earlier(cls, source: Source, ref: Ref) -> Shipment:
        """What a ref a recipient announces shipped, read to compare its copy against and to know
        what has left the manifest since. It is never shipped again, so today's shipping rules —
        the leak rule, the Repository line, the arrival shelf — do not hold it: a ref installed
        before a rule existed would otherwise strand every tree that took it. It carries no
        arrival state; only what is about to ship writes one."""
        return cls(ref, _transformed(source, ref, held=False), "")


def _transformed(source: Source, ref: Ref, held: bool) -> dict[str, str]:
    files: dict[str, str] = {}
    told = resolved(source.repository)
    for path, raw in source.files(ref).items():
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as error:
            raise Refused(f"ship: {path} at {ref.announced} is not UTF-8 — {error}") from error
        files[path] = shipped(path, text, ref, told, held)
    if ENTRY_FILE not in files:
        raise Refused(f"ship: {ref.announced} has no {ENTRY_FILE}; this is not the harness")
    return files


def shipped(path: str, text: str, ref: Ref, told: str, held: bool = True) -> str:
    """One file as a recipient receives it. The order matters: local blocks are found by their tag
    before the shear could touch a wrapper around them, and the leak rule reads the text a
    recipient will. A stamped source is not a citation, which `docs_corpus` settles for every
    reader of it rather than each one blanking the line for itself. Unheld, the file is read as an
    earlier ref shipped it: the same transformation, and none of today's refusals."""
    if path.endswith(".md"):
        text = without_local_blocks(path, text)
        text = sheared(path, text)
        if path == ENTRY_FILE:
            text = stamped(text, ref)
        if path == HARNESS_SKILL and (held or REPOSITORY.search(text)):
            text = repository_stamped(text, ref, told)
        # The front page is the origin's own document, not core text: it ships as written, its
        # links the origin's, and the leak rule does not read it.
        if held and path != INSTALLED_FRONT_PAGE:
            _refuse_leaks(path, [seen.path for seen in docs_mentioned(Path("."), path, text) if not seen.instance_owned])
    elif path.endswith(".py"):
        text = todo_bindings_sheared(text)
        if held and not path.startswith(TESTS):
            try:
                _refuse_leaks(path, [seen.path for seen in docs_mentioned_in_code(text)])
            except UnreadableCode as error:
                raise Refused(f"ship: {path} could not be read for citations — {error}") from error
    return text


def without_local_blocks(path: str, text: str) -> str:
    """The origin's own answers do not travel: every local block leaves with the newline the
    installer added, through the installer's own reading of where a block is."""
    try:
        while (found := inject_rules.locate(text, inject_rules.LOCAL)) is not None:
            if found.text is None:
                raise inject_rules.Refused("the local block opens and never closes")
            text = inject_rules.without_block(text, found)
    except inject_rules.Refused as refusal:
        raise Refused(f"ship: {path}: {refusal}") from refusal
    return text


def without_recipients_blocks(target: Path, path: str, text: str, shipped: dict[str, str]) -> str:
    """What a recipient's installer put in a core file is not an edit in core: the local block
    leaves, and so does the block of every mechanism of the recipient's own — one whose rules
    file stands in the tree and was never shipped. A block no rules file owns stays, and reads
    as the edit it is."""
    text = without_local_blocks(path, text)
    owners = {opening.group(1) for opening in inject_rules.INSTALLED_OPENING.finditer(without_code(text))}
    try:
        for slug in sorted(owners):
            rules = f"{inject_rules.MECHANISMS}/{slug}/{slug}.rules.md"
            if rules in shipped or not (target / rules).is_file():
                continue
            found = inject_rules.locate(text, slug)
            if found.text is None:
                raise inject_rules.Refused(f"the block of {slug} opens and never closes")
            text = inject_rules.without_block(text, found)
    except inject_rules.Refused as refusal:
        raise Refused(f"{path}: {refusal}") from refusal
    return text


def sheared(path: str, text: str) -> str:
    """Every straw-dog wrapper off, its content kept: a recipient gets the rule and never a
    condition it could not observe. A tag alone on its line takes the line; an inline tag leaves
    the text joined as written. Idempotent, so a core already sheared passes unchanged."""
    seen = without_code(text)
    tags = list(TAG.finditer(seen))
    depth = 0
    for tag in tags:
        written = tag.group(0)
        if not written.endswith(">"):
            raise Refused(f"ship: {path}:{_line_at(text, tag.start())} holds a malformed straw-dog tag")
        depth += -1 if written.startswith("</") else 1
        if depth < 0:
            raise Refused(f"ship: {path}:{_line_at(text, tag.start())} closes a straw dog nothing opened")
    if depth:
        raise Refused(f"ship: {path} opens a straw dog it never closes")
    for tag in reversed(tags):
        start, end = _whole_line_if_alone(text, tag.start(), tag.end())
        text = text[:start] + text[end:]
    return text


def todo_bindings_sheared(text: str) -> str:
    """A TODO's question id is its binding, the code form of a straw dog's `question=`; the words
    stay and the id goes, so the recipient reads a note and never an id its store does not hold."""
    lines = []
    for line in text.splitlines(keepends=True):
        named = TODO_QUESTION.match(line)
        lines.append(named.group(1).rstrip() + line[named.end(2) :] if named else line)
    return "".join(lines)


def stamped(text: str, ref: Ref) -> str:
    """The announce line names where core came from; a recipient's every session repeats it."""
    line = ANNOUNCE.search(text)
    if line is None:
        raise Refused(f"ship: {ENTRY_FILE} at {ref.announced} has no announce line; this is not the harness")
    end = line.end("date") + 1  # through the full stop, leaving the line's own ending alone
    return text[: line.start()] + ref.stamp + text[end:]


def repository_stamped(text: str, ref: Ref, told: str) -> str:
    """The harness skill names where this tree's core came from, as the announce line names which
    commit of it. A ref whose skill carries no such line is not the harness, in the same words
    and at the same moment as one whose entry file carries no announce line."""
    line = REPOSITORY.search(text)
    if line is None:
        raise Refused(f"ship: {HARNESS_SKILL} at {ref.announced} has no Repository line; this is not the harness")
    return text[: line.start("url")] + told + text[line.end("url") :]


def arrival_state(files: dict[str, str], ref: Ref) -> str:
    """What the queue says in a tree where core has arrived and nothing is in flight, from the
    ref's own words rather than this tree's: the ticket mechanism owns the record and words it,
    and the only substitution is the ref the recipient will announce.

    Read while the shipment is built, so a ref that cannot say it is refused before anything is
    written rather than partway through. It has a shelf of its own because it is read once, by
    this script, and the format shelf beside it is read at every ticket a session writes. The
    block is found by its info string and not by its position, so prose may be written around it;
    and being fenced is what keeps the citation reader from taking a path inside it for a
    document only the origin has."""
    shelf = files.get(QUEUE_ARRIVAL)
    if shelf is None:
        raise Refused(f"ship: {ref.announced} has no {QUEUE_ARRIVAL}; this is not the harness")
    said = ARRIVAL_STATE.search(shelf)
    if said is None:
        raise Refused(f"ship: {QUEUE_ARRIVAL} at {ref.announced} declares no arrival state")
    return said.group("said").replace("{ref}", ref.announced)


def _refuse_unless_the_roots_are_said(files: dict[str, str], ref: Ref) -> None:
    """A ref whose store shelf cannot say a fresh store's roots is refused while the shipment is
    built, before anything is written, as one whose queue shelf cannot. Where the shelf sits and
    how it is read are the questions mechanism's, asked of its script."""
    shelf = files.get(questions.STORE_ARRIVAL)
    if shelf is None:
        raise Refused(f"ship: {ref.announced} has no shelf at {questions.STORE_ARRIVAL}")
    try:
        questions.arrival_roots(shelf)
    except questions.Refused as refusal:
        raise Refused(f"ship: {ref.announced}: {refusal}") from refusal


def _refuse_unless_the_product_document_is_said(files: dict[str, str], ref: Ref) -> None:
    """A ref whose product shelf cannot say the empty document is refused while the shipment is
    built, as one whose store shelf cannot say the roots. Where the shelf sits and how it is read
    are the product mechanism's, asked of its script."""
    shelf = files.get(product.ARRIVAL)
    if shelf is None:
        raise Refused(f"ship: {ref.announced} has no shelf at {product.ARRIVAL}")
    try:
        product.arrival_document(shelf)
    except product.Refused as refusal:
        raise Refused(f"ship: {ref.announced}: {refusal}") from refusal


def without_repository_line(path: str, text: str) -> str:
    """The recipient's own `--from`, set aside for the comparison. It is the recipient's fact
    living in a core file, as the announce line is, so a check or an update run from another
    source never reads it as an edit. The line leaves with its own newline, as a local block
    does, so what is compared is the text either tree would hold without it."""
    if path != HARNESS_SKILL:
        return text
    return REPOSITORY.sub("", text, count=1)


def _refuse_leaks(path: str, cited: list[str]) -> None:
    leaks = [seen for seen in cited if seen not in PAINTED_DOORS and seen + "/" not in PAINTED_DOORS]
    if leaks:
        raise Refused(f"ship: {path} cites {leaks[0]}, a document only the origin has; it cannot ship")


def _whole_line_if_alone(text: str, start: int, end: int) -> tuple[int, int]:
    line_start = text.rfind("\n", 0, start) + 1
    line_end = text.find("\n", end)
    line_end = len(text) if line_end == -1 else line_end + 1
    if text[line_start:start].strip() or text[end:line_end].strip():
        return start, end
    return line_start, line_end


# --- the target ------------------------------------------------------------------------------


def _work_tree_root(target: Path, source: Source | None, replacing: bool = False) -> Path:
    """One installation is one tree: the target is the top level of a git work tree, and never
    the repository core comes from — unless a clone of it is being replaced, when that is the
    one thing it must be. The link step names no source and copies nothing, so it asks only the
    first."""
    if not target.is_dir():
        raise Refused(f"target: {target} is not a directory")
    target = target.resolve()
    asked = _git_said(target, "rev-parse", "--show-toplevel")
    if asked.returncode != 0 and "dubious ownership" in asked.stderr:
        raise Refused(
            f"target: Git refuses {target} for dubious ownership — run "
            f"`{_safe_directory_command(asked.stderr, target)}`, then run again"
        )
    if asked.returncode != 0 and "not a git repository" in asked.stderr:
        raise Refused(
            f"target: {target} is not a git repository; run git init there, or install at the root you mean, "
            "then run again"
        )
    top = asked.stdout.strip() if asked.returncode == 0 else None
    if top is None:
        raise Refused(f"target: {target} is not the top level of a git work tree; a workspace of several is refused")
    if Path(top).resolve() != target:
        raise Refused(
            f"target: {target} is not the top level of a git work tree; {Path(top).resolve()} is — install there, "
            "or a workspace of several is refused"
        )
    origin = _git_in(target, "remote", "get-url", "origin") if source is not None else None
    is_origin = origin is not None and _same_repository(origin, source.repository)
    if replacing and not is_origin:
        raise Refused(f"replace-clone: {target} is no clone of {source.repository}; --replace-clone is for one")
    if is_origin and not replacing:
        raise Refused(
            f"target: {target} is the source itself; the origin is never installed into — a clean clone "
            "standing where the project was meant takes --install --replace-clone"
        )
    return target


def _clean_clone_head(target: Path) -> str:
    """The commit a clean clone stands at, which the install then ships. A clone holding anything
    of its own is somebody's work, and is refused: a change, an ignored file other than what
    running the harness from it leaves, or a commit on any ref that no remote-tracking branch of
    its origin holds. The remote-tracking branches are read as last fetched, so a stale one can
    only refuse more."""
    somebodys = (
        f"{target} is somebody's work, not a fresh clone; install into the project's own folder "
        "instead, or push what it holds and move the rest out, then run again"
    )
    changed = _git_said(target, "status", "--porcelain", "--ignored=matching")
    if changed.returncode != 0:
        raise Refused(f"replace-clone: git status in {target} failed — {changed.stderr.strip()}")
    own = [line[3:] for line in changed.stdout.splitlines() if not (line.startswith("!! ") and _left_by_running(line[3:]))]
    if own:
        raise Refused(f"replace-clone: {own[0]} is not the origin's — {somebodys}")
    unpushed = _git_said(target, "rev-list", "--count", "--all", "--not", "--remotes=origin")
    if unpushed.returncode != 0 or unpushed.stdout.strip() != "0":
        raise Refused(f"replace-clone: it holds commits its origin's branches lack — {somebodys}")
    head = _git_in(target, "rev-parse", "HEAD")
    if head is None:
        raise Refused(f"replace-clone: {target} has no commit to install from")
    return head


def _left_by_running(ignored: str) -> bool:
    """What a clone of the origin gains by the harness being run from it: the loader links of the
    link step and Python's bytecode caches. Anything else ignored there is the person's."""
    path = ignored.strip('"').rstrip("/")
    return path in LINKS or Path(path).name in ("__pycache__", ".pytest_cache") or path.endswith(".pyc")


def _replace_clone(target: Path, report: Report) -> None:
    """The clone's whole content leaves, its repository with it, and a repository begins afresh:
    the person's folder was empty before the host cloned, so nothing of theirs is here."""
    for child in target.iterdir():
        if child.is_dir() and not child.is_symlink():
            shutil.rmtree(child, onexc=_writable_then_retry)
        else:
            os.chmod(child, stat.S_IWRITE)
            child.unlink()
    made = _git_said(target, "init", "--quiet")
    if made.returncode != 0:
        raise Refused(f"replace-clone: git init in {target} failed — {made.stderr.strip()}")
    report.notes.append(f"replace-clone: {target} held a clean clone of the origin and is now a fresh repository")


def _initialise_if_empty(target: Path, report: Report) -> None:
    """An install into an empty folder inside no repository makes the repository first: the root
    is not in question there, and the person asked for an install. A folder holding anything is
    left for the work-tree check to refuse with the step, since where the root goes is then the
    person's decision. The init is the run's one write outside the manifest, so it is reported."""
    if not target.is_dir() or any(target.iterdir()):
        return
    asked = _git_said(target, "rev-parse", "--show-toplevel")
    if asked.returncode == 0 or "not a git repository" not in asked.stderr:
        return
    made = _git_said(target, "init", "--quiet")
    if made.returncode != 0:
        raise Refused(f"target: git init in {target} failed — {made.stderr.strip()}")
    report.notes.append(f"git init: {target} was not a repository and is now one")


def _safe_directory_command(git_said: str, target: Path) -> str:
    """Git's own command to trust the directory, as it printed it; composed only where Git's
    message does not carry it."""
    for line in git_said.splitlines():
        if line.strip().startswith("git config --global --add safe.directory"):
            return line.strip()
    return f"git config --global --add safe.directory {target.as_posix()}"


def _same_repository(one: str, other: str) -> bool:
    def normalised(named: str) -> str:
        trimmed = named.strip().replace("\\", "/").rstrip("/")
        trimmed = trimmed[:-4] if trimmed.endswith(".git") else trimmed
        local = Path(trimmed)
        if local.exists():
            return str(local.resolve()).replace("\\", "/").lower()
        return trimmed.lower()

    return normalised(one) == normalised(other)


def _refuse_unless_empty(target: Path, shipment: Shipment) -> None:
    present = [path for path in shipment.files if (target / path).exists()]
    if present and (target / HARNESS_SKILL).is_file():
        raise Refused(
            f"install: core is already here — an install, whole or stopped partway; "
            "--update --overwrite completes it"
        )
    if present:
        raise Refused(
            f"install: {present[0]} already exists in the target; a previous install takes --update, "
            "anything else is the recipient's to move first"
        )


def _refuse_unless_updatable(
    target: Path, source: Source, shipment: Shipment, overwrite: bool, report: Report
) -> Shipment | None:
    """What an update must find: core present, no retired tag holding the project's facts, and
    every core file as the announced ref shipped it — or `--overwrite`, which replaces and reports."""
    if not (target / CORE).is_dir():
        raise Refused(f"update: {target} holds no {CORE}; a first install takes --install")
    entry = target / ENTRY_FILE
    if entry.is_file() and RETIRED_TAG in without_code(_read(entry)):
        raise Refused(
            f"update: {ENTRY_FILE} holds a {RETIRED_TAG} block, which is the project's; "
            f"move its content into {LOCAL_FILE} first"
        )
    announced_ref = _announced_ref(target, source, required=False)
    if announced_ref is None:
        if not overwrite:
            raise Refused("update: the tree announces no ref to compare against; --overwrite is required")
        report.notes.append("the tree announced no ref: nothing is deleted, every core file is replaced")
        return None
    previous = Shipment.earlier(source, announced_ref)
    edited = [path for path in previous.files if _differs(target, path, previous.files)]
    if edited and not overwrite:
        raise Refused(
            f"update: {edited[0]} differs from {announced_ref.announced} as installed — an edit in core; "
            "--overwrite replaces it and reports it, or keep the edit in the local file"
        )
    taken = _projects_files_at_added_paths(target, shipment, previous)
    if taken and not overwrite:
        raise Refused(
            f"update: {taken[0]} is the project's own, and {shipment.ref.announced} ships a file there; "
            "--overwrite replaces it and reports it, or move it first"
        )
    report.replaced = edited + taken
    return previous


def _projects_files_at_added_paths(target: Path, shipment: Shipment, previous: Shipment) -> list[str]:
    """The paths this ref adds where the tree already holds something else: the project's own
    files, which the copy would otherwise write over unseen."""
    return [
        path for path in shipment.files
        if path not in previous.files and (target / path).is_file() and not _holds(target, path, shipment.files)
    ]


def _announced_ref(target: Path, source: Source, required: bool) -> Ref | None:
    told = announced(target)
    if told is None:
        if required:
            raise Refused(f"check: {target} announces no <repository>@<ref>; it is not a recipient")
        return None
    if told.repository != source.name:
        raise Refused(f"the tree announces {told.repository}; --from names {source.name}")
    return source.resolve(told.ref)


def _differs(target: Path, path: str, shipped: dict[str, str]) -> bool:
    """Whether the recipient's copy is what the ref shipped, the blocks its own installer put
    there and its own repository line set aside and line endings normalised — the injector's and R2's rule for
    comparing what was installed. Both sides lose the line, so a check or an update run from
    another `--from` reads no edit in core. A missing copy of a root file placed beside core — the
    license, the front page — is no edit: a ref from before either shipped held it at its root all
    the same, so its shipment read today names a copy the tree never received, and the next write
    restores it."""
    copy = target / path
    if not copy.is_file():
        return path not in (INSTALLED_LICENSE, INSTALLED_FRONT_PAGE)
    text = _read(copy)
    shipped_text = shipped[path]
    if path.endswith(".md"):
        try:
            text = without_recipients_blocks(target, path, text, shipped)
        except Refused:
            return True
        text = without_repository_line(path, text)
        shipped_text = without_repository_line(path, shipped_text)
    return _normalised(text) != _normalised(shipped_text)


def _normalised(text: str) -> str:
    return text.replace("\r\n", "\n")


# --- copy, links, inject ---------------------------------------------------------------------


def _holds(target: Path, path: str, shipped: dict[str, str]) -> bool:
    """Whether the copy already holds exactly what ships, the blocks its own installer put there
    set aside: such a
    file is left alone and not reported written, so an update's report names only what changed."""
    copy = target / path
    if not copy.is_file():
        return False
    current = _read(copy)
    if path.endswith(".md"):
        try:
            current = without_recipients_blocks(target, path, current, shipped)
        except Refused:
            return False
    return current == shipped[path]


def _write(target: Path, shipment: Shipment, previous: Shipment | None, report: Report) -> None:
    """Every manifest file, then what left the manifest since the previous ref. A failure partway
    is reported in the mover's form — done, pending, the failed path — and nothing is rolled back."""
    planned = list(shipment.files.items())
    done: list[str] = []
    for path, text in planned:
        if _holds(target, path, shipment.files):
            continue
        try:
            _write_text(target / path, text)
        except OSError as failure:
            pending = [other for other, _ in planned if other not in done and other != path]
            raise Refused(
                f"copy: {path} could not be written — {failure}; done {len(done)}, pending {len(pending)}; "
                "fix the cause and run --update --overwrite"
            ) from failure
        done.append(path)
    report.written = done
    if previous is not None:
        for path in previous.files:
            if path not in shipment.files and (target / path).is_file():
                (target / path).unlink()
                report.deleted.append(path)
        _prune_empty_directories(target / CORE)
    report.own = sorted(
        name for name in corpus(target) if name.startswith(CORE) and name not in shipment.files
    )


def _write_delivery_status(target: Path, shipment: Shipment, report: Report) -> None:
    """The one painted door that arrives with content: a fresh tree's first session reads the
    queue before anything has been written into it, so it must already say something true.

    Written whenever the path is absent — an update is how a tree that received core before this
    acquires one. An existing record is the instance's from its first line: never merged, never
    overwritten, and `--overwrite` does not reach it, since that flag is about core files."""
    record = target / DELIVERY_STATUS
    if record.exists():
        report.notes.append(f"{DELIVERY_STATUS} is the project's: left as it stands")
        return
    record.parent.mkdir(parents=True, exist_ok=True)
    with record.open("w", encoding="utf-8", newline="") as handle:
        handle.write(shipment.arrival)
    report.written.append(DELIVERY_STATUS)


def _seed_store(target: Path, report: Report) -> None:
    """A store holding no entry opens with its roots, on an install or an update alike, as the
    delivery status is written whenever it is absent. The words, the entries and the rule of when
    are the store script's; the installer only calls it (the user, 2026-10-09: no constants in the
    installer). A store holding any entry is the project's and is left."""
    try:
        written = questions.seed(target, datetime.now(timezone.utc))
    except (questions.Refused, questions.WriteInterrupted) as stopped:
        raise Refused(f"{stopped}; run questions.py --seed, then harness.py . --check") from stopped
    report.written += written
    if not written:
        report.notes.append(f"{questions.STORE} holds entries, so it is the project's: left as it stands")


def _seed_product_document(target: Path, report: Report) -> None:
    """A tree with no product document gets the empty one the product shelf words, on an install or
    an update alike; the words and the rule of when are the product script's. One already there is
    the project's, in the format or not, and is left — named when it is not in the format, so the
    first check failing it is no surprise (the user, 2026-10-14)."""
    try:
        written = product.seed(target)
    except product.Refused as stopped:
        raise Refused(f"{stopped}; then harness.py . --check") from stopped
    report.written += written
    if written:
        return
    held = (target / product.DOCUMENT).read_text(encoding="utf-8", errors="replace")
    if product.in_format(held):
        report.notes.append(f"{product.DOCUMENT} is the project's: left as it stands")
    else:
        report.notes.append(
            f"{product.DOCUMENT} is the project's and not in the product format: left as it stands, "
            "and its check fails until it is brought in"
        )


def _wiring_plan(target: Path, shipment: Shipment, previous: Shipment | None) -> dict[str, str]:
    """Each host file's merged text, planned before anything is written so a host file that cannot
    be merged refuses the run with no file changed. A host whose wiring left core since the
    previous ref is planned too: its entries are taken out."""
    shelves = _shelves(shipment)
    before = _shelves(previous) if previous is not None else {}
    plan: dict[str, str] = {}
    for host_file in sorted({*shelves, *before}):
        held = target / host_file
        text = wired(
            host_file,
            _read(held) if held.is_file() else None,
            shelves.get(host_file, "{}"),
            before.get(host_file),
        )
        if text is not None:
            plan[host_file] = text
    return plan


def _shelves(shipment: Shipment) -> dict[str, str]:
    """Core's wiring per host file, read off the shipment: a shelf file's destination is its path
    beneath the questions mechanism's hooks directory. A shelf that is not a hook file is a fault
    of the ref, refused naming it."""
    shelves = {}
    for path, text in shipment.files.items():
        if path.startswith(questions.HOOKS):
            _hook_document(path, text)
            shelves[path[len(questions.HOOKS):]] = text
    return shelves


def _write_wiring(target: Path, plan: dict[str, str], report: Report) -> None:
    for host_file, text in plan.items():
        _write_text(target / host_file, text)
        report.written.append(host_file)


def wired(host_file: str, held: str | None, wiring: str, previous: str | None) -> str | None:
    """A host file with core's hook wiring merged in, or None when it already holds exactly that,
    so an unchanged file is never rewritten.

    The file is shared: the project's own hooks and keys stay where they are. What is core's is
    what the wiring says, compared as JSON values — nothing is written into the file to mark it,
    since JSON has no comments and a marker key is a field the host may reject. An entry the
    previous ref wired and this one does not is taken out; one this ref wires and the file lacks is
    appended; one already present stays where it is, so hooks a person copied by hand count once."""
    current = _hook_document(host_file, held)
    core = _hook_document(f"core's wiring for {host_file}", wiring)
    left = _hook_document(f"the previous wiring for {host_file}", previous).get("hooks", {})
    merged = json.loads(json.dumps(current))
    for key, value in core.items():
        if key == "hooks":
            continue
        if key not in merged:
            merged[key] = value
        elif merged[key] != value:
            raise Refused(f"wire: {host_file} sets {key} to {merged[key]!r} and core's hooks need {value!r}; settle it by hand")
    hooks = merged.setdefault("hooks", {})
    for event, entries in left.items():
        gone = [entry for entry in entries if entry not in core.get("hooks", {}).get(event, [])]
        if event in hooks:
            hooks[event] = [entry for entry in hooks[event] if entry not in gone]
    for event, entries in core.get("hooks", {}).items():
        listed = hooks.setdefault(event, [])
        listed.extend([entry for entry in entries if entry not in listed])
    if held is not None and merged == current:
        return None
    return json.dumps(merged, indent=2, ensure_ascii=False) + "\n"


def holds_wiring(held: str | None, wiring: str) -> bool:
    """Whether a host file holds every entry and key core's wiring names; the project's own are
    never read, so a hook of its own is not drift."""
    try:
        current = _hook_document("the host file", held)
    except Refused:
        return False
    core = json.loads(wiring)
    keys_held = all(current.get(key) == value for key, value in core.items() if key != "hooks")
    hooks = current.get("hooks", {})
    return keys_held and all(
        entry in hooks.get(event, []) for event, entries in core.get("hooks", {}).items() for entry in entries
    )


def _hook_document(name: str, text: str | None) -> dict:
    """A hook file as the hosts read it: an object whose `hooks`, if any, maps each event to a list.
    No text is an empty file; anything else is refused naming it, never rewritten."""
    if text is None:
        return {}
    try:
        document = json.loads(text)
    except json.JSONDecodeError as error:
        raise Refused(f"wire: {name} is not JSON — {error}; fix it by hand and run again") from error
    hooks = document.get("hooks", {}) if isinstance(document, dict) else None
    if not isinstance(hooks, dict) or not all(isinstance(entries, list) for entries in hooks.values()):
        raise Refused(f"wire: {name} is not a hook file — an object whose hooks map each event to a list")
    return document


def _link_plan(target: Path) -> dict[str, str]:
    """Per loader link, before anything is written: `keep`, `make` or `repoint`. A junction, a
    directory or a file where the link goes is the recipient's own and refuses the run."""
    plan: dict[str, str] = {}
    skills = (target / SKILLS).resolve()
    for link in LINKS:
        path = target / link
        # Asked of the link itself, never through it: a dangling junction or symlink has no
        # `exists()` and is still something standing where the link goes.
        if _is_junction(path):
            raise Refused(f"link: {link} is a junction, which nothing sees through; remove it, a symlink goes there")
        if path.is_symlink():
            plan[link] = "keep" if _resolves_to(path, skills) or _written_to(path, skills) else "repoint"
        elif not os.path.lexists(path):
            plan[link] = "make"
        else:
            raise Refused(f"link: {link} is a {'directory' if path.is_dir() else 'file'} of the recipient's own; move it first")
    return plan


def _make_links(target: Path, plan: dict[str, str], report: Report) -> None:
    """A symlink, or the exact command for the person: the platform's refusal is the one step of an
    install that may be left to a hand, and it does not stop the rest. A link being repointed is
    removed only once its replacement exists: one the platform will not replace stays standing."""
    for link, action in plan.items():
        path = target / link
        if action == "keep":
            report.links.append({"link": link, "state": "kept"})
            continue
        made = path.with_name(f"{path.name}.gw-new") if action == "repoint" else path
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            os.symlink(LINK_TARGET.replace("/", os.sep), made, target_is_directory=True)
        except OSError as failure:
            pending = {"link": link, "state": "pending", "error": str(failure)}
            if action == "repoint":
                pending |= {"stands": True, "was": _link_text(path)}
            report.links.append(pending)
            report.pending.append(_link_command(path, replacing=action == "repoint"))
            continue
        if action == "repoint":
            was = _link_text(path)
            _remove_link(path)
            os.replace(made, path)
            report.links.append({"link": link, "state": "repointed", "was": was})
            continue
        report.links.append({"link": link, "state": "made"})
    if report.pending:
        report.notes.append(
            "run the pending command(s) once in an elevated prompt, then `harness.py . --links`, which reports whether each resolves"
        )


def _exclude_links(target: Path, plan: dict[str, str], report: Report) -> None:
    """Every planned link is named in the clone's exclude file, the pending ones too, so the
    person's later command makes a link `git add -A` never stages. The links are never committed;
    the origin's ignore file does not ship, and the exclude file is the clone's as the links are.
    Git names the file, since a work tree made by `git worktree` keeps its `.git` elsewhere."""
    named = _git_in(target, "rev-parse", "--git-path", "info/exclude")
    if named is None:
        report.notes.append("git named no exclude file: the links may show as untracked")
        return
    exclude = target / named if not Path(named).is_absolute() else Path(named)
    present = _read(exclude).splitlines() if exclude.is_file() else []
    missing = [link for link in plan if link not in present]
    if missing:
        text = "".join(f"{line}\n" for line in present + missing)
        _write_text(exclude, text)
    report.excluded = list(plan)


def _record_interpreter(target: Path, report: Report) -> None:
    """The interpreter running this step, which runs by that fact, recorded for the hooks: a bare
    `python` may be the Windows Store stub, macOS and Linux may carry only `python3`, and `uv` is
    one machine's habit. A record naming an interpreter that still exists is the person's choice
    and stays; one naming a missing path is rewritten."""
    named = _git_in(target, "rev-parse", "--git-path", INTERPRETER_RECORD)
    if named is None:
        report.notes.append("git named no directory for the interpreter record: the hooks will say so")
        return
    record = target / named if not Path(named).is_absolute() else Path(named)
    held = _read(record).strip() if record.is_file() else ""
    if held and Path(held).is_file():
        report.interpreter = {"record": held, "state": "kept"}
        return
    _write_text(record, f"{sys.executable}\n")
    report.interpreter = {"record": sys.executable, "state": "written"}


def _remove_link(path: Path) -> None:
    # Windows removes a directory symlink through rmdir, not unlink; the link itself goes, never its target.
    try:
        path.unlink()
    except OSError:
        os.rmdir(path)


def _link_text(path: Path) -> str | None:
    try:
        return os.readlink(path)
    except OSError:
        return None


def _link_command(path: Path, replacing: bool = False) -> str:
    if os.name == "nt":
        make = f'mklink /D "{path}" "{LINK_TARGET.replace("/", os.sep)}"'
        return f'rmdir "{path}" && {make}' if replacing else make
    make = f'ln -s {LINK_TARGET} "{path}"'
    return f'rm "{path}" && {make}' if replacing else make


def _inject(target: Path, report: Report) -> None:
    """The rules files installed into the copy. The preflight asked the same of a rehearsal, so a
    refusal here is one it could not foresee; the run has written, and the resume is the local
    file, the injector, then --check."""
    refused = _install_rules(target, report.injected)
    if refused:
        slug, reason = refused
        raise Refused(
            f"inject: {slug}: {reason}; fix {LOCAL_FILE}, run inject_rules.py {slug} --install, "
            "then harness.py . --check"
        )


def _refuse_unless_injectable(target: Path, shipment: Shipment, previous: Shipment | None) -> None:
    """The injection rehearsed before a byte of the target is written, over a scratch tree holding
    the rules files and the files they target as the copy will leave them: a refusal the injector
    would give after the copy is the run's refusal now. The scratch tree is a repository of its
    own, as the target is: the injector lists a tree by Git, and the system's temporary folder is
    inside none."""
    with tempfile.TemporaryDirectory(prefix="harness-rehearsal-") as scratch:
        rehearsal = Path(scratch)
        _git_said(rehearsal, "init", "--quiet")
        for path, text in _injection_inputs(target, shipment, previous).items():
            _write_text(rehearsal / path, text)
        refused = _install_rules(rehearsal, [])
    if refused:
        slug, reason = refused
        raise Refused(f"inject: {slug}: {reason}; nothing was written — fix {LOCAL_FILE}, then run again")


def _install_rules(root: Path, injected: list[dict]) -> tuple[str, str] | None:
    """Every mechanism's rules file, then the recipient's local file last, each recorded in
    `injected` as it lands; the first refusal, by the slug of the file refused, ends it."""
    sources = [directory.name for directory in sorted((root / inject_rules.MECHANISMS).glob("*/"))
               if (directory / f"{directory.name}.rules.md").is_file()]
    if (root / LOCAL_FILE).is_file():
        sources.append(inject_rules.LOCAL)
    for slug in sources:
        try:
            rules = inject_rules.read_rules_file(root, slug)
            if slug == inject_rules.LOCAL:
                inject_rules.overrides_resolve(root, rules)
            outcome = inject_rules.install(root, rules, overwrite=False)
        except inject_rules.Refused as refusal:
            return slug, str(refusal)
        injected.append({"slug": slug, "targets": outcome["targets"]})
        if outcome["refusals"]:
            return slug, outcome["refusals"][0]
    return None


def _injection_inputs(target: Path, shipment: Shipment, previous: Shipment | None) -> dict[str, str]:
    """What the injection will read once the copy is done: every rules file — shipped, the
    recipient's own mechanisms' that stay, the local file — and every file their anchor tables
    name, each as the copy leaves it. A file the target holds as shipped stays as it stands, its
    installed blocks with it; a file leaving the manifest is gone."""
    leaving = set(previous.files) - set(shipment.files) if previous else set()

    def after_copy(path: str) -> str | None:
        if path in shipment.files:
            return _read(target / path) if _holds(target, path, shipment.files) else shipment.files[path]
        if path in leaving or not (target / path).is_file():
            return None
        return _read(target / path)

    held_rules = (path.relative_to(target).as_posix() for path in (target / inject_rules.MECHANISMS).glob("*/*.rules.md"))
    rules_files = {path for path in [*shipment.files, *held_rules] if _is_rules_file(path)} | {LOCAL_FILE}
    inputs = {}
    for path in sorted(rules_files):
        text = after_copy(path)
        if text is None:
            continue
        inputs[path] = text
        slug = inject_rules.LOCAL if path == LOCAL_FILE else path.split("/")[2]
        try:
            anchored = inject_rules.parse_rules_file(slug, text).anchors
        except inject_rules.Refused:
            continue  # the rehearsal reads it again, and its refusal is the run's
        for anchored_path in anchored:
            held = after_copy(anchored_path)
            if held is not None:
                inputs[anchored_path] = held
    return inputs


def _is_rules_file(path: str) -> bool:
    """A mechanism's rules file: `<mechanisms>/<slug>/<slug>.rules.md`."""
    parts = path.split("/")
    return path.startswith(inject_rules.MECHANISMS + "/") and len(parts) == 4 and parts[3] == f"{parts[2]}.rules.md"


# --- the gate --------------------------------------------------------------------------------


def _gate(target: Path, shipment: Shipment, report: Report) -> None:
    """Arrival, and any later day's question, are one function: the ref compared, the injector's
    check, the shape check — the target's own scripts, run as subprocesses, so what is checked
    is what arrived, in seconds. The loader links are reported beside the verdict, resolving or
    not, and never decide it: a link the platform refused is the person's one remaining step,
    and the command for it is already in the report. The shipped suite is not run here; a
    recipient that wants it names it in its own verification set."""
    gates = {
        "ref": _ref_gate(target, shipment),
        "injector": _script_gate(target, "inject_rules.py"),
        "shape": _script_gate(target, "mechanisms.py"),
    }
    report.gates = gates
    report.links_resolve = _links_resolve(target)
    report.arrived = all(gate["passed"] for gate in gates.values())
    report.notes.append("whether a host reads the loader link is not observable from inside a tree")


def _ref_gate(target: Path, shipment: Shipment) -> dict:
    differing = [path for path in shipment.files if _differs(target, path, shipment.files)]
    differing += [
        host_file for host_file, wiring in _shelves(shipment).items()
        if not holds_wiring(_read(target / host_file) if (target / host_file).is_file() else None, wiring)
    ]
    own =sorted(name for name in corpus(target) if name.startswith(CORE) and name not in shipment.files)
    return {"passed": not differing, "ref": shipment.ref.announced, "differs": differing, "own": own}


def _script_gate(target: Path, script: str) -> dict:
    """A gate is the script's own verdict, and what it says is the script's diagnostics — the
    reason, whole, so the person never runs the check again to find it. A script that printed no
    report, having crashed, is quoted by its last lines instead."""
    done = _python(target, [str(target / SCRIPTS / script), "--check"])
    return {"passed": done.returncode == 0, "exit": done.returncode, "said": _diagnostics(done)}


def _diagnostics(done: subprocess.CompletedProcess) -> list:
    try:
        report = json.loads(done.stdout or "")
    except json.JSONDecodeError:
        report = None
    if isinstance(report, dict) and isinstance(report.get("diagnostics"), list):
        return report["diagnostics"]
    return _last_lines(done.stdout or done.stderr)


def _links_resolve(target: Path) -> dict[str, bool]:
    """Per loader link, whether a symlink stands there and reaches a directory of skill files."""
    return {
        link: (target / link).is_symlink() and (target / link).is_dir() and any((target / link).glob("*/SKILL.md"))
        for link in LINKS
    }


def _python(target: Path, arguments: list[str]) -> subprocess.CompletedProcess:
    environment = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    return subprocess.run(
        [sys.executable, *arguments], cwd=target, capture_output=True, encoding="utf-8", env=environment
    )


def _last_lines(text: str | None, keep: int = 3) -> list[str]:
    return [line for line in (text or "").strip().splitlines() if line][-keep:]


# --- helpers ---------------------------------------------------------------------------------


def _git_said(target: Path, *arguments: str) -> subprocess.CompletedProcess:
    """Git's whole answer: a refusal names its cause on stderr, and one caller reads it."""
    return subprocess.run(["git", "-C", str(target), *arguments], capture_output=True, encoding="utf-8")


def _git_in(target: Path, *arguments: str) -> str | None:
    done = _git_said(target, *arguments)
    return done.stdout.strip() if done.returncode == 0 else None


def _resolves_to(link: Path, skills: Path) -> bool:
    try:
        return link.resolve() == skills and link.is_dir()
    except OSError:
        return False


def _written_to(link: Path, skills: Path) -> bool:
    """Whether the link's own text names the skills directory, asked without following it: a
    process that cannot see through a link, as inside a sandbox, still reads where it points."""
    text = _link_text(link)
    if text is None:
        return False
    pointed = os.path.normpath(os.path.join(link.parent.resolve(), text.removeprefix("\\\\?\\")))
    return os.path.normcase(pointed) == os.path.normcase(str(skills))


def _is_junction(path: Path) -> bool:
    try:
        return os.lstat(path).st_reparse_tag == stat.IO_REPARSE_TAG_MOUNT_POINT
    except (AttributeError, OSError):
        return False


def _prune_empty_directories(top: Path) -> None:
    for directory in sorted((path for path in top.rglob("*") if path.is_dir()), reverse=True):
        if not any(directory.iterdir()):
            directory.rmdir()


def _line_at(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _read(path: Path) -> str:
    with path.open(encoding="utf-8", newline="") as handle:
        return handle.read()


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write(text)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
