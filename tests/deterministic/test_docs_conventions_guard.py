"""Guard: cross-artifact conventions hold (docs/cicd.md § CI pipeline).

Three agreements, each between artifacts that describe one another and drift apart silently:

- a code comment's doc pointer keeps resolving — a `#NN` concern ref names a live concern (a ref
  to a settled concern's gap is the dangling-premise defect), an `ADR-NNNN` ref names a real ADR,
  and a `.md` mention is the one canonical repo-root form, `docs/edge/provider.md`;
- the delivery queue and the ticket folders agree — a `Done` row links into `done/` and only such
  rows do, a closed ticket has every acceptance box checked, an open ticket has work left;
- a session record carries its own identity — the filename's number and date appear among those
  its H1 names (H1 date spellings like `2026-07-24/25` and `... → 2026-08-16` count for both days).

This module and its siblings are excluded from the pointer scan: their fixtures and patterns are
illustrations, not citations.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path

from docs_corpus import REPO_ROOT, universe

_POINTER_EXEMPT = frozenset(
    {
        "docs_corpus.py",
        "test_docs_integrity_guard.py",
        "test_docs_conventions_guard.py",
        "test_record_mover.py",
    }
)
_CONCERNS = "docs/concerns.md"
_QUEUE = "docs/tickets/README.md"

_CONCERN_REF = re.compile(r"#(\d{2,3})\b")
_CONCERN_ENTRY = re.compile(r"^## (\d+)\.", re.MULTILINE)
_ADR_REF = re.compile(r"ADR-(\d{4})")
_ADR_FILE = re.compile(r"^docs/adr/(\d{4})-")
_MD_MENTION = re.compile(r"[\w./-]*\w\.md\b")
_QUEUE_POSITION = re.compile(r"(?:\d{2}-)?\d{4}(?:\.\d{4})*")
_ROW_TICKET = re.compile(r"\]\((\./[^)]*\.md)\)")
_CHECKBOX = re.compile(r"^\s*- \[([ x])\]", re.MULTILINE)
_SESSION_FILE = re.compile(r"^docs/sessions/(?:history/\d{4}-\d{2}/)?(\d{4})-(\d{8})-[^/]+\.md$")
_H1_NUMBER = re.compile(r"\b(\d{4})\b")
_H1_DATE = re.compile(r"(\d{4}-\d{2}-\d{2})(?:/(\d{2}))?")


def _pointer_defects(root: Path, names: Sequence[str]) -> list[str]:
    """Code comments that point at documentation nobody can follow anymore."""
    members = set(names)
    concerns = _concern_ids(root)
    adrs = {m.group(1) for n in names if (m := _ADR_FILE.match(n))}
    defects: list[str] = []
    for name in sorted(names):
        if not (name.startswith(("src/", "tests/")) and name.endswith(".py")):
            continue
        if name.rsplit("/", 1)[-1] in _POINTER_EXEMPT:
            continue
        text = (root / name).read_text(encoding="utf-8")
        for ref in _CONCERN_REF.findall(text):
            if ref not in concerns:
                defects.append(f"{name}: #{ref} names no live concern")
        for ref in _ADR_REF.findall(text):
            if ref not in adrs:
                defects.append(f"{name}: ADR-{ref} names no ADR")
        for mention in _MD_MENTION.findall(text):
            if mention not in members:
                defects.append(f"{name}: {mention} is not a repo-root document path")
    return defects


def _concern_ids(root: Path) -> set[str]:
    registry = root / _CONCERNS
    if not registry.is_file():
        return set()
    return set(_CONCERN_ENTRY.findall(registry.read_text(encoding="utf-8")))


def _queue_defects(root: Path, names: Sequence[str]) -> list[str]:
    """Disagreements between the delivery map and the ticket folders it narrates."""
    queue = root / _QUEUE
    if not queue.is_file():
        return [f"{_QUEUE}: missing"]
    defects: list[str] = []

    row_targets: list[str] = []
    for position, ticket_cell, status in _delivery_rows(queue.read_text(encoding="utf-8")):
        link = _ROW_TICKET.search(ticket_cell)
        if link is None:
            defects.append(f"{_QUEUE}: row {position} carries no ticket link")
            continue
        target = "docs/tickets/" + link.group(1)[2:]
        row_targets.append(target)
        if status.startswith("Done") != ("/done/" in target):
            defects.append(f"{_QUEUE}: row {position} status '{status}' disagrees with {target}")

    tickets = {
        n
        for n in names
        if re.fullmatch(r"docs/tickets/(?:done/)?[^/]+\.md", n) and not n.endswith("README.md")
    }
    for missing in sorted(tickets - set(row_targets)):
        defects.append(f"{_QUEUE}: no delivery-map row for {missing}")
    for extra in sorted(set(row_targets) - tickets):
        defects.append(f"{_QUEUE}: row links {extra}, which is no ticket file")

    for name in sorted(tickets):
        boxes = _CHECKBOX.findall((root / name).read_text(encoding="utf-8"))
        if "/done/" in name and " " in boxes:
            defects.append(f"{name}: closed with an open acceptance box")
        if "/done/" not in name and boxes and " " not in boxes:
            defects.append(f"{name}: every box checked, but the ticket has not moved to done/")
    return defects


def _delivery_rows(text: str) -> list[tuple[str, str, str]]:
    """(position, ticket cell, status) for every delivery-map row of the queue document."""
    rows: list[tuple[str, str, str]] = []
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) >= 6 and _QUEUE_POSITION.fullmatch(cells[0]):
            rows.append((cells[0], cells[1], cells[3]))
    return rows


def _session_defects(root: Path, names: Sequence[str]) -> list[str]:
    """Session records whose filename and H1 disagree about number or date."""
    defects: list[str] = []
    for name in sorted(names):
        match = _SESSION_FILE.match(name)
        if match is None:
            continue
        number, stamp = match.groups()
        h1 = (root / name).read_text(encoding="utf-8").partition("\n")[0]
        if not h1.startswith("# "):
            defects.append(f"{name}: no H1 to carry its identity")
            continue
        h1_number = _H1_NUMBER.search(h1)
        if h1_number is None or h1_number.group(1) != number:
            defects.append(f"{name}: H1 does not open with session number {number}")
        date = f"{stamp[:4]}-{stamp[4:6]}-{stamp[6:]}"
        if date not in _h1_dates(h1):
            defects.append(f"{name}: H1 does not name the filename date {date}")
    return defects


def _h1_dates(h1: str) -> set[str]:
    dates: set[str] = set()
    for day, second_day in _H1_DATE.findall(h1):
        dates.add(day)
        if second_day:
            dates.add(day[:8] + second_day)
    return dates


# --- synthetic corpora: every rule proven by the reason it fires ---


def _corpus(tmp_path: Path, files: dict[str, str]) -> list[str]:
    for name, content in files.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return sorted(files)


def test_settled_concern_reference_is_reported(tmp_path: Path) -> None:
    names = _corpus(
        tmp_path,
        {"docs/concerns.md": "## 21. Alive\n", "src/x.py": "# see #21; premise gone at #22\n"},
    )
    (defect,) = _pointer_defects(tmp_path, names)
    assert "#22" in defect and "no live concern" in defect


def test_missing_adr_reference_is_reported(tmp_path: Path) -> None:
    names = _corpus(
        tmp_path, {"docs/adr/0001-x.md": "# X", "src/x.py": "# ADR-0001 holds; ADR-0099 does not\n"}
    )
    (defect,) = _pointer_defects(tmp_path, names)
    assert "ADR-0099" in defect


def test_non_canonical_md_mention_is_reported(tmp_path: Path) -> None:
    names = _corpus(
        tmp_path,
        {"docs/architecture.md": "# A", "src/x.py": "# see architecture.md\n"},
    )
    (defect,) = _pointer_defects(tmp_path, names)
    assert "architecture.md is not a repo-root document path" in defect


def test_canonical_pointers_pass(tmp_path: Path) -> None:
    names = _corpus(
        tmp_path,
        {
            "docs/architecture.md": "# A",
            "docs/concerns.md": "## 21. Alive\n",
            "docs/adr/0001-x.md": "# X",
            "src/x.py": "# docs/architecture.md, #21, ADR-0001\n",
        },
    )
    assert _pointer_defects(tmp_path, names) == []


def test_done_row_linking_outside_done_is_reported(tmp_path: Path) -> None:
    queue = "| # | Ticket | Kind | Status | Depends on | Outcome |\n|---|---|---|---|---|---|\n| 0010 | [T](./01-0010-t.md) | — | Done | — | x |\n"
    names = _corpus(tmp_path, {_QUEUE: queue, "docs/tickets/01-0010-t.md": "- [x] all\n"})
    defects = _queue_defects(tmp_path, names)
    assert any("disagrees with docs/tickets/01-0010-t.md" in d for d in defects)


def test_closed_ticket_with_open_box_is_reported(tmp_path: Path) -> None:
    queue = "| 0010 | [T](./done/01-0010-t.md) | — | Done | — | x |\n"
    names = _corpus(tmp_path, {_QUEUE: queue, "docs/tickets/done/01-0010-t.md": "- [ ] open\n"})
    defects = _queue_defects(tmp_path, names)
    assert any("closed with an open acceptance box" in d for d in defects)


def test_fully_checked_active_ticket_is_reported(tmp_path: Path) -> None:
    queue = "| 0010 | [T](./01-0010-t.md) | — | Ready | — | x |\n"
    names = _corpus(tmp_path, {_QUEUE: queue, "docs/tickets/01-0010-t.md": "- [x] done\n"})
    defects = _queue_defects(tmp_path, names)
    assert any("has not moved to done/" in d for d in defects)


def test_unmapped_ticket_and_ticketless_row_are_reported(tmp_path: Path) -> None:
    queue = "| 0010 | [T](./01-0010-gone.md) | — | Ready | — | x |\n"
    names = _corpus(tmp_path, {_QUEUE: queue, "docs/tickets/01-0020-unlisted.md": "- [ ] w\n"})
    defects = _queue_defects(tmp_path, names)
    assert any("no delivery-map row for docs/tickets/01-0020-unlisted.md" in d for d in defects)
    assert any("which is no ticket file" in d for d in defects)


def test_session_date_disagreement_is_reported(tmp_path: Path) -> None:
    names = _corpus(
        tmp_path,
        {"docs/sessions/0009-20260812-x.md": "# 0009 · 2026-08-11 · carried yesterday's date\n"},
    )
    (defect,) = _session_defects(tmp_path, names)
    assert "2026-08-12" in defect


def test_session_spellings_for_split_and_ranged_days_pass(tmp_path: Path) -> None:
    names = _corpus(
        tmp_path,
        {
            "docs/sessions/0017-20260725-x.md": "# 0017 · 2026-07-24/25 · split day\n",
            "docs/sessions/history/2026-08/0028-20260816-x.md": (
                "# 0028 · 2026-08-11 (evening) → 2026-08-16 · a stretch\n"
            ),
        },
    )
    assert _session_defects(tmp_path, names) == []


# --- the live gates ---


def test_conventions_corpus_is_discovered() -> None:
    """A guard that guards nothing passes silently — pin that the registries are populated."""
    names = universe(REPO_ROOT)
    text = "".join(
        (REPO_ROOT / n).read_text(encoding="utf-8")
        for n in names
        if n.startswith(("src/", "tests/"))
        and n.endswith(".py")
        and n.rsplit("/", 1)[-1] not in _POINTER_EXEMPT
    )
    assert len(_CONCERN_REF.findall(text)) >= 25, "concern refs went missing from code"
    assert len(_ADR_REF.findall(text)) >= 50, "ADR refs went missing from code"
    assert len(_delivery_rows((REPO_ROOT / _QUEUE).read_text(encoding="utf-8"))) >= 10
    assert sum(1 for n in names if _SESSION_FILE.match(n)) >= 20


def test_code_pointers_resolve() -> None:
    defects = _pointer_defects(REPO_ROOT, universe(REPO_ROOT))
    assert not defects, "\n".join(defects)


def test_queue_and_folders_agree() -> None:
    defects = _queue_defects(REPO_ROOT, universe(REPO_ROOT))
    assert not defects, "\n".join(defects)


def test_session_records_dated() -> None:
    defects = _session_defects(REPO_ROOT, universe(REPO_ROOT))
    assert not defects, "\n".join(defects)
