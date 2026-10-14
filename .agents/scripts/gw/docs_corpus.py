# Mechanism: mechanism-shape
"""What the repository's records are, and where their citations point.

The maintenance scripts share one view of the tree: every file Git speaks for, and the markdown
citation grammar those files are written in. Both take an explicit repository root, so a synthetic
corpus in a temporary directory runs through the exact code the live tree runs through.
"""

from __future__ import annotations

import io
import posixpath
import re
import subprocess
import tokenize
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from urllib.parse import quote, unquote

_INLINE = re.compile(r'(!?\[[^\]]*\]\(\s*)(<[^>]*>|[^)\s]+)((?:\s+(?:"[^"]*"|\'[^\']*\'|\([^)]*\)))?\s*\))', re.S)
_DEFINITION = re.compile(r'(^[ ]{0,3}\[[^\]]+\]:[ \t]*)(<[^>]*>|\S+)((?:[ \t]+(?:"[^"]*"|\'[^\']*\'|\([^)]*\)))?[ \t]*$)', re.M)
# A straw dog binds to the question whose answer will rewrite it, by that question's id.
_QUESTION_BINDING = re.compile(r'(<straw-dog\b[^<>]*?\bquestion\s*=\s*")([^"]*)(")', re.S)
# In code the binding is the id a `TODO` comment line names first: `# TODO q-0018.0010: …`.
TODO_QUESTION = re.compile(r"^(\s*#\s*TODO\s+)(q-[\d.]*\d)(?![\w.])")
# A straw dog's attribute, as written: the question it waits on. One grammar for the lister and
# the mechanism check, so both read what a rename rewrites.
ATTRIBUTE = re.compile(r'\b(question)\s*=\s*"([^"]*)"', re.S)
_WRAPPED_WHOLE = re.compile(r"^<straw-dog\b([^<>]*)>(.*)</straw-dog\s*>$", re.S)
# The installed block's tag, shared with the injector that writes it and the listing that skips it.
INSTALLED_OPENING = re.compile(r'<installed by="([^"]+)">')
INSTALLED_CLOSING = "</installed>"
_FENCE = re.compile(r"^\s*(```|~~~)")
_CODE_SPAN = re.compile(r"`[^`]*`")
_ELSEWHERE = re.compile(r"^(?:https?|mailto|ftps?|tel|data|news|irc):|^//|^#")
_DRIVE = re.compile(r"^[A-Za-z]:/")
# What core may name under `docs/` is AGENTS.md § Core and instance; this module reads the mentions
# and `mechanisms.py` rules on them. A path is a token from `docs/` over path characters, so a
# sentence ending in one keeps its full stop and `docs/` followed by an ellipsis is no path at all.
PATH_LITERAL = re.compile(r"docs/\w[\w./-]*")
# The repository a tree's core came from, stamped into the harness skill at install. It is a
# source, never a citation: a clone on disk under a `docs/` directory would otherwise be read as
# a document only the origin has, and every recipient installed from such a path would fail its
# own shape check.
_STAMPED_SOURCE = re.compile(r"^Repository: \S+[ \t]*$", re.M)
_TRAILING_PUNCTUATION = ".,;:"
# The instance-owned block: the project's rules as the installer writes them from its local file.
# The `<project-local>` tag an author once wrote is retired and excuses nothing; `mechanisms.py`
# reports one left in core.
_INSTANCE_OWNED = re.compile(r"<installed by=\"local\">.*?</installed>", re.S)
RETIRED_TAG = "<project-local>"
_WRAPPER_OPENING = re.compile(r"<straw-dog\b[^<>]*>")
# The entry file's announce line, which every session repeats. At the origin it carries a
# hand-bumped version; in a recipient the harness mechanism stamps it `<repository>@<ref>`, and that `@` is
# the one mark that tells the two trees apart — no record file, the line is the revision.
ANNOUNCE = re.compile(r"^Entry contract: (?P<revision>[^,\r\n]+), (?P<date>\d{4}-\d{2}-\d{2})\.[ \t]*\r?$", re.M)
ENTRY_FILE = "AGENTS.md"
# Where a tree's straw dogs stand: what `/maintain` lists, what the wake reads for the due ones,
# and where a rename carries their bindings.
STRAW_DOG_SCOPE = ("docs", "AGENTS.md", "local.rules.md", ".agents", "README.md")
# Core's scripts sit under a directory of their own, so an install into a tree that already has
# scripts beside them writes next to the project's and never over one.
SCRIPTS = ".agents/scripts/gw/"
_CODE_TOKENS = {tokenize.STRING, tokenize.COMMENT} | (
    {tokenize.FSTRING_MIDDLE} if hasattr(tokenize, "FSTRING_MIDDLE") else set()
)


@dataclass(frozen=True)
class Target:
    """Where one citation points, in the pieces a record move can change.

    `path` is decoded and slash-separated so two spellings of the same file compare equal; `scheme`,
    `separator` and `encoded` remember how the citation was written, so re-aiming it changes the
    destination and nothing else about its form.
    """

    scheme: str
    path: str
    fragment: str
    separator: str
    encoded: bool
    elsewhere: bool

    @property
    def absolute(self) -> bool:
        return bool(_DRIVE.match(self.path)) or self.path.startswith("/")

    def aimed_at(self, path: str) -> str:
        """The same citation, written the same way, pointing at `path`."""
        written = path.replace("/", self.separator)
        if self.encoded:
            written = quote(written, safe="/\\:")
        return self.scheme + written + self.fragment


def target_of(written: str) -> Target:
    """Read a citation's written destination. A `file:` URI is local; an `https:` one is elsewhere."""
    path, marker, anchor = written.partition("#")
    fragment = marker + anchor
    if _ELSEWHERE.match(written):
        return Target("", path, fragment, "/", False, elsewhere=True)
    scheme = ""
    if path[:5].lower() == "file:":
        body = path[5:]
        slashes = len(body) - len(body.lstrip("/"))
        # `file:///D:/…` and `file:///docs/…` differ only in what follows the slashes; keep them
        # verbatim in the scheme so the rebuilt URI is byte-identical outside the path.
        keep = slashes if _DRIVE.match(body[slashes:]) else max(slashes - 1, 0)
        scheme, path = "file:" + body[:keep], body[keep:]
    separator = "\\" if "\\" in path and "/" not in path else "/"
    encoded = "%" in path
    if encoded:
        path = unquote(path)
    return Target(scheme, path.replace("\\", "/"), fragment, separator, encoded, elsewhere=False)


def cited_record(root: Path, citing: str, target: Target) -> str | None:
    """The root-relative record a citation names, or `None` when it points outside this repository.

    An absolute path or a `file:` URI to a record in this tree is the same citation as a relative
    one — syntax alone cannot excuse it from a move.
    """
    if target.elsewhere or not target.path:
        return None
    if not target.absolute:
        return posixpath.normpath(posixpath.join(posixpath.dirname(citing), target.path))
    try:
        inside = Path(target.path).resolve().relative_to(root.resolve())
    except (OSError, ValueError):
        return None
    return inside.as_posix()


def corpus(root: Path) -> list[str]:
    """Every file the repository speaks for: tracked plus untracked-but-unignored, exact case.

    Exact-case names come from Git so case drift a Windows working tree hides stays visible, and
    untracked files are included so a record minted this session resolves before `git add`.
    """
    listing = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=root,
        capture_output=True,
        encoding="utf-8",
        check=True,
    )
    seen: dict[str, None] = {}
    for name in listing.stdout.split("\0"):
        if name and (root / name).is_file():
            seen.setdefault(name, None)
    return list(seen)


def with_citations_retargeted(text: str, retarget) -> str:
    """Every prose citation re-aimed by `retarget`; a `None` answer leaves that citation alone.

    Fenced blocks and inline code are illustrations of the syntax, not promises about a file, so
    they are never rewritten.
    """
    return _outside_code(text, lambda prose: _prose_retargeted(prose, retarget))


@dataclass(frozen=True)
class Wrapper:
    """One straw dog wrapped around a whole span of text — a table cell, typically.

    `question` is as written, or `None` where the tag binds none; `body` is what the tag wraps, and
    what survives the install spec's shear.
    """

    question: str | None
    body: str


def wrapper_of(text: str) -> Wrapper | None:
    """The straw dog wrapping all of `text`, or `None` where the text is not wholly wrapped.

    A tag that wraps part of a span is a straw dog on that part and is the lister's to walk; this
    reads only the case where the wrapper *is* the span's form, as a `not yet` row's is.
    """
    found = _WRAPPED_WHOLE.match(text.strip())
    if found is None:
        return None
    return Wrapper(dict(ATTRIBUTE.findall(found.group(1))).get("question"), found.group(2).strip())


def question_bindings(root: Path) -> list[tuple[str, int, str]]:
    """Every operative binding to a question where a tree's straw dogs stand, as `(record, line,
    id)` in record order. A path of the scope the tree lacks is no straw dog's, never an error."""
    found: list[tuple[str, int, str]] = []
    for name in corpus(root):
        if in_straw_dog_scope(name):
            found += [(name, line, question) for line, question in bindings_in(name, read_text(root, name))]
    return found


def bindings_in(name: str, text: str) -> list[tuple[int, str]]:
    """One record's bindings to a question, as `(line, id)`: a `TODO q-N` line in a script, a straw
    dog's tag outside code in a document."""
    if name.endswith(".py"):
        return [
            (number, named.group(2))
            for number, line in enumerate(text.splitlines(), start=1)
            if (named := TODO_QUESTION.match(line))
        ]
    return [(_line_at(text, bound.start()), bound.group(2)) for bound in _QUESTION_BINDING.finditer(without_code(text))]


def read_text(root: Path, name: str) -> str:
    """A record's text as the binding scan reads it: undecodable bytes replaced, never refused."""
    return (root / name).read_bytes().decode("utf-8", errors="replace")


def in_straw_dog_scope(name: str) -> bool:
    """Whether a record is a document or a script where straw dogs stand."""
    return name.endswith((".md", ".py")) and any(
        name == prefix or name.startswith(f"{prefix}/") for prefix in STRAW_DOG_SCOPE
    )


def with_question_bindings_retargeted(name: str, text: str, retarget) -> str:
    """Every operative binding to a question in the record `name` re-aimed by `retarget`, which is
    given an id and returns the id it now has, or `None` to leave it.

    A document's binding is its `<straw-dog question="…">`; a script's is the id its `TODO` lines
    name first. An illustration of the syntax — in a fence or a code span — binds nothing and is left
    alone, so an id in an example keeps its value.
    """
    if name.endswith(".py"):
        return _todo_bindings_retargeted(text, retarget)
    return _outside_code(text, lambda prose: _prose_bindings_retargeted(prose, retarget))


def _outside_code(text: str, rewrite: Callable[[str], str]) -> str:
    """Apply `rewrite` to the document's prose, passing fenced blocks through untouched."""
    rewritten: list[str] = []
    prose: list[str] = []
    inside_fence = False
    for line in text.splitlines(keepends=True):
        if _FENCE.match(line):
            rewritten.append(rewrite("".join(prose)))
            prose.clear()
            rewritten.append(line)
            inside_fence = not inside_fence
        elif inside_fence:
            rewritten.append(line)
        else:
            prose.append(line)
    rewritten.append(rewrite("".join(prose)))
    return "".join(rewritten)


def _prose_bindings_retargeted(text: str, retarget) -> str:
    code_spans = [span.span() for span in _CODE_SPAN.finditer(text)]

    def rewritten(match: re.Match[str]) -> str:
        if any(start <= match.start(2) < end for start, end in code_spans):
            return match.group(0)
        final = retarget(match.group(2))
        return match.group(0) if final is None else match.group(1) + final + match.group(3)

    return _QUESTION_BINDING.sub(rewritten, text)


def _todo_bindings_retargeted(text: str, retarget) -> str:
    lines = text.splitlines(keepends=True)
    for at, line in enumerate(lines):
        named = TODO_QUESTION.match(line)
        final = retarget(named.group(2)) if named else None
        if final is not None:
            lines[at] = named.group(1) + final + line[named.end(2) :]
    return "".join(lines)


def citations(text: str) -> list[str]:
    """Every destination this module recognises as a citation, in document order.

    Reads through the one grammar `with_citations_retargeted` rewrites, so nothing can be checked
    that would not also have been repaired.
    """
    found: list[str] = []

    def collect(target: str) -> None:
        found.append(target)
        return None

    with_citations_retargeted(text, collect)
    return found


def without_code(text: str) -> str:
    """The same text, character for character, with every code span and fenced block blanked out.

    Positions are preserved so a search over the result still points at the real line, and an
    illustration of a path can never be mistaken for a claim about a file.
    """
    kept: list[str] = []
    inside_fence = False
    for line in text.splitlines(keepends=True):
        if _FENCE.match(line):
            inside_fence = not inside_fence
            kept.append(_blanked(line))
        elif inside_fence:
            kept.append(_blanked(line))
        else:
            kept.append(_CODE_SPAN.sub(lambda span: _blanked(span.group(0)), line))
    return "".join(kept)


def _blanked(text: str) -> str:
    return "".join(character if character in "\r\n" else " " for character in text)


def _prose_retargeted(text: str, retarget) -> str:
    """Both citation forms that name a file: the inline link and the reference definition."""
    code_spans = [span.span() for span in _CODE_SPAN.finditer(text)]

    def rewritten(match: re.Match[str]) -> str:
        if any(start <= match.start(2) < end for start, end in code_spans):
            return match.group(0)
        bracketed = match.group(2).startswith("<") and match.group(2).endswith(">")
        target = match.group(2)[1:-1] if bracketed else match.group(2)
        final = retarget(target)
        if final is None:
            return match.group(0)
        return match.group(1) + (f"<{final}>" if bracketed else final) + match.group(3)

    return _DEFINITION.sub(rewritten, _INLINE.sub(rewritten, text))


@dataclass(frozen=True)
class Announced:
    """What a recipient's entry file says it received: the repository's name and the ref."""

    repository: str
    ref: str


def announced(root: Path) -> Announced | None:
    """The `<repository>@<ref>` a tree's entry file announces, or `None` at the origin — whose
    line carries a version and no `@` — and where there is no entry file or no line at all."""
    entry = root / ENTRY_FILE
    if not entry.is_file():
        return None
    line = ANNOUNCE.search(entry.read_text(encoding="utf-8"))
    if line is None or "@" not in line.group("revision"):
        return None
    repository, _, ref = line.group("revision").partition("@")
    return Announced(repository.strip(), ref.strip())


@dataclass(frozen=True)
class Mention:
    """One path under `docs/` a core file names — by citation or as a bare literal — and whether an
    instance-owned block holds it, which is the only thing that excuses it."""

    line: int
    path: str
    instance_owned: bool


class UnreadableCode(Exception):
    """A script the tokenizer could not read. The caller reports it: a skip is not a pass."""


def docs_mentioned(root: Path, citing: str, text: str) -> list[Mention]:
    """Every path under `docs/` a document names, in document order.

    Two readings of one text, positions shared. Tags are found through `without_code`, so a tag
    written in a code span is an illustration and never a block. Paths are found with fences
    blanked, so a path in a code span is the claim this corpus writes it as. A straw dog's opening
    tag is blanked — its binding is not a citation — and what it wraps is read, because the shear
    ships it. A citation resolving outside `docs/` is not this reading's business.
    """
    tagged = without_code(text)
    owned = [span.span() for span in _INSTANCE_OWNED.finditer(tagged)]
    openings = [span.span() for span in _WRAPPER_OPENING.finditer(tagged)]
    stamped = [span.span() for span in _STAMPED_SOURCE.finditer(tagged)]
    readable = _blanked_spans(_without_fences(text), openings + stamped)
    found: list[tuple[int, int, str]] = []
    for start, target in _citations_at(readable):
        record = cited_record(root, citing, target_of(target))
        if record and record.startswith("docs/"):
            found.append((start, start + len(target), record))
    for token in PATH_LITERAL.finditer(_blanked_spans(readable, [(start, end) for start, end, _ in found])):
        found.append((token.start(), token.end(), token.group(0).rstrip(_TRAILING_PUNCTUATION)))
    return [
        Mention(_line_at(text, start), path, any(begin <= start < end for begin, end in owned))
        for start, _, path in sorted(found)
    ]


def docs_mentioned_in_code(text: str) -> list[Mention]:
    """Every path under `docs/` a script names in a string or a comment.

    A `TODO` binds a question by its id, never a path, so a path in one is a citation like any
    other. Raises `UnreadableCode` where the tokenizer fails.
    """
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(text).readline))
    except (tokenize.TokenError, SyntaxError) as error:
        raise UnreadableCode(str(error)) from error
    found = []
    for token in tokens:
        if token.type in _CODE_TOKENS:
            for literal in PATH_LITERAL.finditer(token.string):
                found.append(Mention(token.start[0], literal.group(0).rstrip(_TRAILING_PUNCTUATION), False))
    return found


def _citations_at(text: str) -> list[tuple[int, str]]:
    """Where each citation's destination starts, and what it says — outside code spans, as the rewriter reads."""
    code_spans = [span.span() for span in _CODE_SPAN.finditer(text)]
    found = []
    for pattern in (_INLINE, _DEFINITION):
        for match in pattern.finditer(text):
            if any(start <= match.start(2) < end for start, end in code_spans):
                continue
            target = match.group(2)
            bracketed = target.startswith("<") and target.endswith(">")
            found.append((match.start(2) + (1 if bracketed else 0), target[1:-1] if bracketed else target))
    return found


def _without_fences(text: str) -> str:
    """The same text, positions preserved, with fenced blocks blanked and code spans kept."""
    kept: list[str] = []
    inside_fence = False
    for line in text.splitlines(keepends=True):
        if _FENCE.match(line):
            inside_fence = not inside_fence
            kept.append(_blanked(line))
        else:
            kept.append(_blanked(line) if inside_fence else line)
    return "".join(kept)


def _blanked_spans(text: str, spans: list[tuple[int, int]]) -> str:
    kept = list(text)
    for start, end in spans:
        for at in range(start, end):
            if kept[at] not in "\r\n":
                kept[at] = " "
    return "".join(kept)


def _line_at(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1
