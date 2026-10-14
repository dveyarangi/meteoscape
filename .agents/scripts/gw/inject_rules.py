# Mechanism: mechanism-shape
"""A mechanism's rules reach other skills as installed blocks, from the one file that holds them.

    uv run --offline --no-project python .agents/scripts/gw/inject_rules.py <slug> --install [--overwrite]
    uv run --offline --no-project python .agents/scripts/gw/inject_rules.py <slug> --retract
    uv run --offline --no-project python .agents/scripts/gw/inject_rules.py --check

One block per source per target, holding every rule the source sends there. A source is a
mechanism's rules file, or the project's own — `local.rules.md` beside the entry file, the slug
`local` — whose block lands after every mechanism's in a target and whose rules may name the
core rule each overrides. The grammar of the rules file is the format shelf's,
`MECHANISM-FORMAT.md`; the contract — a named mode or a refusal, every target validated before
anything is written, retraction byte-identical, a differing block refused until the caller says
overwrite — is the architecture's.

The script never decides what a rule means and never writes a doc.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from docs_corpus import (  # noqa: E402  (path set just above)
    INSTALLED_CLOSING,
    INSTALLED_OPENING,
    citations,
    corpus,
    without_code,
)

MECHANISMS = ".agents/mechanisms"
# The project's own rules file: beside the entry file, outside core, so a redeploy that replaces
# the core directory cannot delete it. Its slug is the block tag the leak check already skips.
LOCAL = "local"
LOCAL_FILE = "local.rules.md"
MODES = ("--install", "--retract", "--check")
_USAGE = "usage: inject_rules.py <slug> --install [--overwrite] | <slug> --retract | --check"
_HEADING = re.compile(r"^(#{1,6}) (.*)$", re.M)
_WRAPPER_OPENING = re.compile(r"^<straw-dog\b[^<>]*>$")
_TABLE_ROW = re.compile(r"^\|\s*`([^`]+)`\s*\|\s*`([^`]+)`\s*\|\s*$")
_TARGET = re.compile(r"^- \*\*target\*\* `([^`]+)`\s*$")
_OVERRIDES = re.compile(r"^- \*\*overrides\*\* `([^`/]+)/([^`/]+)`\s*$")
_AUTHORITY = re.compile(r"^- \*\*authority\*\* (.+?)\s*$")
_SPAN_EDGE = re.compile(r"^</?rule>\r?\n?$")


class Refused(Exception):
    """Something that must not be written past. The message says what to settle first."""


@dataclass(frozen=True)
class Rule:
    id: str
    title: str
    targets: tuple[str, ...]
    authority: str
    body: str
    overrides: tuple[str, str] | None = None
    """The core rule this one replaces, as (slug, id) — a project's override names its rule."""

    @property
    def paragraph(self) -> str:
        """As installed: the id, the rule it overrides where it does, so a reader sees the
        disagreement where they meet it, and the body unreshaped."""
        cited = f" *(overrides {'/'.join(self.overrides)})*" if self.overrides else ""
        return f"**{self.id}**{cited} {self.body}"


@dataclass(frozen=True)
class RulesFile:
    """One mechanism's rules, with the place in each target its block goes."""

    slug: str
    anchors: dict[str, str]
    rules: tuple[Rule, ...]

    def block(self, target: str) -> str:
        """What the target must hold: every rule naming it, file order, ids from the headings."""
        paragraphs = [rule.paragraph for rule in self.rules if target in rule.targets]
        return f'<installed by="{self.slug}">\n' + "\n\n".join(paragraphs) + f"\n{INSTALLED_CLOSING}"


@dataclass(frozen=True)
class Located:
    """A block found in a target by its tag. `text` is None when the tag never closes."""

    start: int
    end: int
    text: str | None


def main(argv: list[str], root: Path) -> int:
    slug, mode, overwrite, usage = _parsed(argv)
    if usage:
        print(_USAGE)
        return 2
    if mode == "--check":
        report = check(root)
        print(json.dumps(report, indent=2))
        return 1 if report["diagnostics"] else 0
    try:
        rules = read_rules_file(root, slug)
        if mode == "--install":
            overrides_resolve(root, rules)
    except Refused as refusal:
        print(json.dumps({"slug": slug, "mode": mode[2:], "refusals": [str(refusal)]}, indent=2))
        return 1
    report = install(root, rules, overwrite) if mode == "--install" else retract(root, rules)
    print(json.dumps(report, indent=2))
    return 1 if report["refusals"] else 0


def _parsed(argv: list[str]) -> tuple[str | None, str | None, bool, bool]:
    """Exactly one mode, always named; the slug present exactly when the mode needs it."""
    modes = [operand for operand in argv if operand in MODES]
    flags = [operand for operand in argv if operand.startswith("-") and operand not in MODES]
    words = [operand for operand in argv if not operand.startswith("-")]
    overwrite = flags == ["--overwrite"]
    if len(modes) != 1 or (flags and not overwrite):
        return None, None, False, True
    mode = modes[0]
    if mode == "--check":
        return None, mode, False, bool(words) or overwrite
    if len(words) != 1 or (overwrite and mode != "--install"):
        return None, mode, overwrite, True
    return words[0], mode, overwrite, False


# --- the rules file --------------------------------------------------------------------------


def read_rules_file(root: Path, slug: str) -> RulesFile:
    if slug == LOCAL and (root / MECHANISMS / LOCAL).is_dir():
        raise Refused(_COLLISION)
    path = _rules_path(root, slug)
    if not path.is_file():
        raise Refused(f"no rules file at {path.relative_to(root).as_posix()}")
    return parse_rules_file(slug, _read(path))


def _rules_path(root: Path, slug: str) -> Path:
    """A mechanism's file sits in its directory; the project's sits beside the entry file."""
    if slug == LOCAL:
        return root / LOCAL_FILE
    return root / MECHANISMS / slug / f"{slug}.rules.md"


_COLLISION = f"a mechanism directory named {LOCAL} collides with the local file {LOCAL_FILE}"


def parse_rules_file(slug: str, text: str) -> RulesFile:
    """The shelf's grammar, one line at a time.

    What kind of line it is — heading, bullet, table row, span edge — is decided on the
    code-blanked view, so an example in a fence is never a rule; what it says is read from the
    raw line, since the values are code spans and the blanked view has erased them.
    """
    lines = list(zip(text.splitlines(keepends=True), without_code(text).splitlines(keepends=True)))
    starts = _section_starts(lines)
    if not starts:
        raise Refused("no rule sections — an install of nothing is not a success")
    anchors = _anchor_table(lines[: starts[0]])
    rules = [
        _rule(lines[start:end], anchors)
        for start, end in zip(starts, starts[1:] + [len(lines)])
    ]
    ids = [rule.id for rule in rules]
    for rule_id in ids:
        if ids.count(rule_id) > 1:
            raise Refused(f"rule id {rule_id} appears twice")
    return RulesFile(slug, anchors, tuple(rules))


def _section_starts(lines: list[tuple[str, str]]) -> list[int]:
    """Every `## ` line outside a span. One inside a span is refused here, where it is seen first."""
    starts: list[int] = []
    inside_span = False
    for index, (_, seen) in enumerate(lines):
        if _SPAN_EDGE.match(seen):
            inside_span = seen.startswith("<rule>")
        elif seen.startswith("## "):
            if inside_span:
                raise Refused("a rule's body holds a heading line")
            starts.append(index)
    return starts


def _anchor_table(preamble: list[tuple[str, str]]) -> dict[str, str]:
    anchors: dict[str, str] = {}
    for raw, seen in preamble:
        row = _TABLE_ROW.match(raw)
        if row is None or seen.replace("|", "").strip():
            continue  # not a row of two code spans: the header, the divider, or prose
        target, anchor = row.group(1), row.group(2)
        if target in anchors:
            raise Refused(f"{target} is named twice in the anchor table — a mechanism has one place in a target")
        anchors[target] = anchor
    return anchors


def _rule(section: list[tuple[str, str]], anchors: dict[str, str]) -> Rule:
    heading = section[0][0][3:].strip()
    rule_id, _, title = heading.partition(" — ")
    rule_id = rule_id.strip()
    targets: list[str] = []
    overrides: list[tuple[str, str]] = []
    authorities: list[str] = []
    edges: list[int] = []
    for index, (raw, seen) in enumerate(section[1:], start=1):
        if seen.startswith("- **target**") and (match := _TARGET.match(raw)):
            targets.append(match.group(1))
        elif seen.startswith("- **overrides**") and (match := _OVERRIDES.match(raw)):
            overrides.append((match.group(1), match.group(2)))
        elif seen.startswith("- **authority**") and (match := _AUTHORITY.match(raw)):
            authorities.append(match.group(1))
        elif _SPAN_EDGE.match(seen):
            edges.append(index)
    if not targets:
        raise Refused(f"rule {rule_id} names no target")
    for target in targets:
        if target not in anchors:
            raise Refused(f"rule {rule_id} targets {target}, which has no row in the anchor table")
    if len(overrides) > 1:
        raise Refused(f"rule {rule_id} states overrides more than once")
    if len(authorities) != 1:
        raise Refused(f"rule {rule_id} must state its authority exactly once")
    if len(edges) != 2 or [section[i][1].rstrip("\r\n") for i in edges] != ["<rule>", "</rule>"]:
        raise Refused(f"rule {rule_id} needs exactly one <rule> … </rule> span")
    body = "".join(raw for raw, _ in section[edges[0] + 1 : edges[1]]).rstrip("\r\n")
    _body_problems(rule_id, body)
    return Rule(rule_id, title.strip(), tuple(targets), authorities[0], body, overrides[0] if overrides else None)


def overrides_resolve(root: Path, rules: RulesFile) -> None:
    """Every override names a rule that exists and is sent to every target the override names.

    Read from the cited rules file's declared targets, never from whether its block is present:
    an absent mechanism block is that mechanism's diagnostic, and the override's refusal names
    the local entry so the author knows which one to fix.
    """
    for problem in override_problems(root, rules):
        raise Refused(problem)


def override_problems(root: Path, rules: RulesFile) -> list[str]:
    """Each override that names no rule the tree installs where the override goes, in file order."""
    problems = []
    for rule in rules.rules:
        if rule.overrides is None:
            continue
        slug, cited_id = rule.overrides
        said = f"{rule.id} overrides {slug}/{cited_id}"
        try:
            cited = read_rules_file(root, slug)
        except Refused as refusal:
            problems.append(f"{said}, but {refusal}")
            continue
        found = next((one for one in cited.rules if one.id == cited_id), None)
        if found is None:
            problems.append(f"{said}, which {slug}'s rules file does not define")
            continue
        problems += [
            f"{said}, which is not installed in {target}"
            for target in rule.targets
            if target not in found.targets
        ]
    return problems


def _body_problems(rule_id: str, body: str) -> None:
    # A citation is rewritten per the file it sits in, so one body in two directories would drift
    # apart on the next record move; a heading would split the section; the tag would end the block.
    if citations(body):
        raise Refused(f"rule {rule_id}'s body carries a citation; name paths in words or backticks")
    if _HEADING.search(body):
        raise Refused(f"rule {rule_id}'s body holds a heading line")
    if "<installed" in body or INSTALLED_CLOSING in body:
        raise Refused(f"rule {rule_id}'s body holds the installed tag")
    # A body is copied into every target, and the listing blanks an installed block before it
    # scans: a straw dog written here would be invisible in every place it landed. An expiring
    # rule is wrapped around its section instead, where the rule is authored and the listing looks.
    if "<straw-dog" in body or "</straw-dog>" in body:
        raise Refused(
            f"rule {rule_id}'s body holds a straw dog; wrap the section, not the body, so the "
            "listing sees it where the rule is authored"
        )


# --- the target -----------------------------------------------------------------------------


def locate(text: str, slug: str) -> Located | None:
    """The block by its tag — never by its body, which an edit would hide from us."""
    seen = without_code(text)
    openings = [m for m in INSTALLED_OPENING.finditer(seen) if m.group(1) == slug]
    if not openings:
        return None
    if len(openings) > 1:
        raise Refused(f"two blocks of {slug} in one file")
    start = openings[0].start()
    close = seen.find(INSTALLED_CLOSING, start)
    if close == -1:
        return Located(start, -1, None)
    end = close + len(INSTALLED_CLOSING)
    return Located(start, end, text[start:end])


def matches(found: str, rendered: str) -> bool:
    # Both sides normalised, in one place: Life's injector and its wake normalised one side each
    # and disagreed about the same blocks for a week.
    return found.replace("\r\n", "\n") == rendered.replace("\r\n", "\n")


def after_anchor(text: str, anchor: str) -> int:
    """The offset just past the anchor line's newline; the line must be whole, terminated, unique."""
    seen = without_code(text)
    hits = []
    offset = 0
    for line in seen.splitlines(keepends=True):
        if line.rstrip("\r\n") == anchor:
            if not line.endswith("\n"):
                raise Refused(f"anchor {anchor!r} is the last line and has no newline to install after")
            hits.append(offset + len(line))
        offset += len(line)
    if not hits:
        raise Refused(f"anchor {anchor!r} not found")
    if len(hits) > 1:
        raise Refused(f"anchor {anchor!r} is ambiguous — it occurs {len(hits)} times")
    return hits[0]


def section_end(text: str, anchor: str) -> int:
    """The offset just past the last non-blank line of the anchor's section: the section runs
    from the anchor line to the next heading of the anchor's level or higher, or to the end of
    the text; a line that is not a heading is ended by any heading. Fences are not read. A straw
    dog opening on a line of its own with nothing of the section after it wraps what follows, so
    it is the next section's: a block placed after it would expire with text it does not belong to."""
    start = after_anchor(text, anchor)
    seen = without_code(text)
    level = _heading_level(anchor)
    end = start
    offset = start
    for line in seen[start:].splitlines(keepends=True):
        heading = _heading_level(line.rstrip("\r\n"))
        if heading is not None and heading <= (level if level is not None else 6):
            break
        offset += len(line)
        if line.strip() and not _WRAPPER_OPENING.match(line.strip()):
            end = offset
    return end


def _heading_level(line: str) -> int | None:
    match = _HEADING.match(line)
    return len(match.group(1)) if match else None


def insertion_point(text: str, anchor: str, slug: str) -> int:
    """At the end of the anchor's section, so blocks stand in install order after the section's
    own text — and, for a mechanism's block, before the local block if one is already there, so
    the project's answer stays what a reader meets after core's rules."""
    end = section_end(text, anchor)
    if slug == LOCAL:
        return end
    local = locate(text, LOCAL)
    if local is not None and after_anchor(text, anchor) <= local.start < end:
        return local.start - 1
    return end


def following_block(text: str, offset: int) -> tuple[str, int] | None:
    """The first installed block opening at or after `offset`: its slug and line, or None."""
    seen = without_code(text)
    for opening in INSTALLED_OPENING.finditer(seen):
        if opening.start() >= offset:
            return opening.group(1), text.count("\n", 0, opening.start()) + 1
    return None


def with_block(text: str, at: int, block: str) -> str:
    return text[:at] + "\n" + block + "\n" + text[at:]


def without_block(text: str, found: Located) -> str:
    """Exactly what install added: the block, the newline before it, the newline after it."""
    start, end = found.start, found.end
    if not (start >= 1 and text[start - 1] == "\n" and text[end:end + 1] == "\n"):
        raise Refused("the block is not spaced as the installer writes it")
    return text[: start - 1] + text[end + 1:]


# --- the modes ------------------------------------------------------------------------------


def install(root: Path, rules: RulesFile, overwrite: bool) -> dict:
    """Every target validated first; then, only if all of them passed, every target written."""
    return _installing_or_retracting(root, rules, "install", overwrite)


def retract(root: Path, rules: RulesFile) -> dict:
    return _installing_or_retracting(root, rules, "retract", False)


def _installing_or_retracting(root: Path, rules: RulesFile, mode: str, overwrite: bool) -> dict:
    planned: list[tuple[str, str]] = []
    outcomes: list[dict] = []
    refusals: list[str] = []
    for target, anchor in rules.anchors.items():
        try:
            outcome, new_text = _planned(root, rules, target, anchor, mode, overwrite)
        except Refused as refusal:
            refusals.append(f"{target}: {refusal}")
            continue
        outcomes.append(outcome)
        if new_text is not None:
            planned.append((target, new_text))
    if mode == "install":
        for dropped in _dropped_targets(root, rules):
            try:
                outcome, new_text = _removal(root, rules.slug, dropped)
            except Refused as refusal:
                refusals.append(f"{dropped}: {refusal}")
                continue
            outcomes.append(outcome)
            planned.append((dropped, new_text))
    report = {"slug": rules.slug, "mode": mode, "targets": outcomes, "refusals": refusals}
    if refusals:
        return report
    return _written(root, planned, report)


def _planned(
    root: Path, rules: RulesFile, target: str, anchor: str, mode: str, overwrite: bool
) -> tuple[dict, str | None]:
    path = root / target
    if not path.is_file():
        raise Refused("target missing")
    text = _read(path)
    found = locate(text, rules.slug)
    if found is not None and found.text is None:
        raise Refused("the block opens and never closes")
    rendered = rules.block(target)
    if mode == "install":
        if found is None:
            at = insertion_point(text, anchor, rules.slug)
            if rules.slug == LOCAL and (follows := following_block(text, at)):
                raise Refused(
                    f"the local block would not be last: a block of {follows[0]} at line {follows[1]} "
                    "would follow it; anchor the local rule after every mechanism's block"
                )
            return {"target": target, "state": "installed"}, with_block(text, at, rendered)
        if matches(found.text, rendered):
            return {"target": target, "state": "present"}, None
        if not overwrite:
            raise Refused(
                "the block differs from the rules file — an amended source not yet installed, or a "
                "copy edited in place; the tool cannot tell, so say --overwrite and read what it replaced"
            )
        replaced = text[: found.start] + rendered + text[found.end:]
        return {"target": target, "state": "overwritten", "replaced": found.text}, replaced
    if found is None:
        return {"target": target, "state": "absent"}, None
    if not matches(found.text, rendered):
        raise Refused(
            "the block differs from the rules file; reconcile the source, install with --overwrite, "
            "then retract"
        )
    return {"target": target, "state": "retracted"}, without_block(text, found)


def _dropped_targets(root: Path, rules: RulesFile) -> list[str]:
    """Every file holding a block of this source that the source no longer names: a target dropped
    from the rules file, whose block the check would report as one nothing owns."""
    return [
        name for name in corpus(root)
        if name.endswith(".md") and name not in rules.anchors
        and any(opening.group(1) == rules.slug for opening in INSTALLED_OPENING.finditer(without_code(_read(root / name))))
    ]


def _removal(root: Path, slug: str, target: str) -> tuple[dict, str]:
    """The block taken out by the retraction's own cut, so the file is what it was before the
    block was installed. It is installed, never authored, so nothing is asked; what it held is
    reported, as an overwrite reports what it replaced."""
    text = _read(root / target)
    found = locate(text, slug)
    if found is None or found.text is None:
        raise Refused("the block opens and never closes")
    return {"target": target, "state": "removed", "removed": found.text}, without_block(text, found)


def _written(root: Path, planned: list[tuple[str, str]], report: dict) -> dict:
    # The mover's contract: on a failure after mutation starts, stop and say what landed and what
    # did not. Nothing is rolled back; the maintainer inspects the files.
    done: list[str] = []
    for target, new_text in planned:
        try:
            _write(root / target, new_text)
        except OSError as failure:
            pending = [other for other, _ in planned if other not in done and other != target]
            report["refusals"] = [f"{target}: could not be written — {failure}"]
            report["done"] = done
            report["pending"] = pending
            return report
        done.append(target)
    return report


def check(root: Path) -> dict:
    """Every rules file against every target it names, and every block against the rules files."""
    files: dict[str, RulesFile | None] = {}
    blocks: list[dict] = []
    diagnostics: list[str] = []
    for directory in sorted((root / MECHANISMS).glob("*/")) if (root / MECHANISMS).is_dir() else []:
        slug = directory.name
        if slug == LOCAL:
            diagnostics.append(f"{slug}: {_COLLISION}")
            continue
        if not (directory / f"{slug}.rules.md").is_file():
            continue
        try:
            files[slug] = read_rules_file(root, slug)
        except Refused as refusal:
            files[slug] = None
            diagnostics.append(f"{slug}: {refusal}")
    if (root / LOCAL_FILE).is_file():
        try:
            files[LOCAL] = read_rules_file(root, LOCAL)
        except Refused as refusal:
            files[LOCAL] = None
            diagnostics.append(f"{LOCAL}: {refusal}")
    for slug, rules in files.items():
        if rules is None:
            continue
        diagnostics.extend(f"{slug}: {problem}" for problem in override_problems(root, rules))
        for target, anchor in rules.anchors.items():
            state = _state(root, rules, target, anchor)
            blocks.append({"slug": slug, "target": target, "state": state})
            if state != "present":
                diagnostics.append(f"{slug} in {target}: {state}")
    orphans = _orphans(root, files)
    diagnostics.extend(f"orphan block of {slug} in {path}" for slug, path in orphans)
    return {
        "rules files": len(files),
        "blocks": blocks,
        "orphans": [{"slug": slug, "file": path} for slug, path in orphans],
        "diagnostics": diagnostics,
    }


def _state(root: Path, rules: RulesFile, target: str, anchor: str) -> str:
    path = root / target
    if not path.is_file():
        return "target missing"
    text = _read(path)
    try:
        found = locate(text, rules.slug)
    except Refused as refusal:
        return str(refusal)
    if found is None:
        try:
            after_anchor(text, anchor)
        except Refused as refusal:
            return "anchor ambiguous" if "ambiguous" in str(refusal) else "anchor missing"
        return "absent"
    if found.text is None:
        return "the block opens and never closes"
    if not matches(found.text, rules.block(target)):
        return "drifted"
    if rules.slug == LOCAL and following_block(text, found.end):
        return "not last"
    return "present"


def _orphans(root: Path, files: dict[str, RulesFile | None]) -> list[tuple[str, str]]:
    """A block whose slug has no rules file, or whose rules file does not send it to that file."""
    orphans = []
    for name in corpus(root):
        if not name.endswith(".md"):
            continue
        seen = without_code(_read(root / name))
        for opening in INSTALLED_OPENING.finditer(seen):
            slug = opening.group(1)
            rules = files.get(slug)
            if slug not in files or (rules is not None and name not in rules.anchors):
                orphans.append((slug, name))
    return orphans


def _read(path: Path) -> str:
    with path.open(encoding="utf-8", newline="") as handle:
        return handle.read()


def _write(path: Path, text: str) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write(text)


if __name__ == "__main__":
    # The tree this script sits in; anything that imports it names its tree itself.
    sys.exit(main(sys.argv[1:], Path(__file__).resolve().parents[3]))
