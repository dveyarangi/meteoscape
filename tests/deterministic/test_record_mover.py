"""The mechanical record mover: moves are link-true, judgment-free, and prose-identical.

Covers `.agents/scripts/move_doc.py` through synthetic corpora and a filesystem move, with the
integrity guard's own defect finder as the proof that a moved corpus links cleanly — the same
instrument that proves a real move (docs/cicd.md § CI pipeline).
"""

from __future__ import annotations

import sys
from pathlib import Path

from docs_corpus import REPO_ROOT
from test_docs_integrity_guard import _link_defects

sys.path.insert(0, str(REPO_ROOT / ".agents" / "scripts"))

import move_doc


def _corpus(tmp_path: Path, files: dict[str, str]) -> list[str]:
    for name, content in files.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="")
    return sorted(files)


def _fs_move(root: Path, source: str, destination: str) -> None:
    target = root / destination
    target.parent.mkdir(parents=True, exist_ok=True)
    (root / source).rename(target)


def _read(root: Path, name: str) -> str:
    return (root / name).read_text(encoding="utf-8", newline="")


def test_closing_a_ticket_redepths_it_and_its_citers_follow(tmp_path: Path) -> None:
    names = _corpus(
        tmp_path,
        {
            "docs/concerns.md": "## 21. Alive",
            "docs/tickets/01-0001-t.md": "# H\n[c](../concerns.md#21-alive)\n[sib](./01-0002-o.md)",
            "docs/tickets/01-0002-o.md": "# Other",
            "docs/tickets/README.md": "[t](./01-0001-t.md#h)\n",
            "docs/tickets/done/01-0000-old.md": "# Done",
        },
    )
    pairs = [("docs/tickets/01-0001-t.md", "docs/tickets/done/01-0001-t.md")]
    assert move_doc.refusal(pairs, names) is None
    move_doc.perform(tmp_path, names, pairs, move=_fs_move)

    moved = _read(tmp_path, "docs/tickets/done/01-0001-t.md")
    assert "[c](../../concerns.md#21-alive)" in moved
    assert "[sib](../01-0002-o.md)" in moved
    assert _read(tmp_path, "docs/tickets/README.md") == "[t](./done/01-0001-t.md#h)\n"

    after = [n for n in names if n != pairs[0][0]] + [pairs[0][1]]
    assert _link_defects(tmp_path, after) == []


def test_paired_close_cites_final_homes(tmp_path: Path) -> None:
    names = _corpus(
        tmp_path,
        {
            "docs/tickets/01-0001-t.md": "Plan: [rfc](../rfc/01-0001-t.md)",
            "docs/rfc/01-0001-t.md": "Implements [t](../tickets/01-0001-t.md).",
        },
    )
    pairs = [
        ("docs/rfc/01-0001-t.md", "docs/rfc/done/01-0001-t.md"),
        ("docs/tickets/01-0001-t.md", "docs/tickets/done/01-0001-t.md"),
    ]
    move_doc.perform(tmp_path, names, pairs, move=_fs_move)
    assert "[rfc](../../rfc/done/01-0001-t.md)" in _read(tmp_path, "docs/tickets/done/01-0001-t.md")
    assert "[t](../../tickets/done/01-0001-t.md)" in _read(tmp_path, "docs/rfc/done/01-0001-t.md")


def test_only_link_paths_change(tmp_path: Path) -> None:
    body = (
        "# T\r\n\r\n- [x] done box\r\n- [ ] open box\r\n\r\n"
        "```md\r\n[example](../concerns.md)\r\n```\r\n"
        "`[inline](../concerns.md)` and [real](../concerns.md)\r\n"
    )
    names = _corpus(tmp_path, {"docs/tickets/01-0001-t.md": body, "docs/concerns.md": "# C"})
    move_doc.perform(
        tmp_path, names, [("docs/tickets/01-0001-t.md", "docs/tickets/done/01-0001-t.md")], _fs_move
    )
    assert _read(tmp_path, "docs/tickets/done/01-0001-t.md") == body.replace(
        "[real](../concerns.md)", "[real](../../concerns.md)"
    )


def test_historical_citers_stay_as_written(tmp_path: Path) -> None:
    session = "# 0001 · 2026-01-01 · x\n[t](../tickets/01-0001-t.md)\n"
    names = _corpus(
        tmp_path,
        {"docs/sessions/0001-20260101-x.md": session, "docs/tickets/01-0001-t.md": "# T"},
    )
    move_doc.perform(
        tmp_path, names, [("docs/tickets/01-0001-t.md", "docs/tickets/done/01-0001-t.md")], _fs_move
    )
    assert _read(tmp_path, "docs/sessions/0001-20260101-x.md") == session


def test_session_archiving_redepths_into_history(tmp_path: Path) -> None:
    names = _corpus(
        tmp_path,
        {
            "docs/sessions/0001-20260101-x.md": "[a](../architecture.md)",
            "docs/architecture.md": "# A",
        },
    )
    move_doc.perform(
        tmp_path,
        names,
        [("docs/sessions/0001-20260101-x.md", "docs/sessions/history/2026-01/0001-20260101-x.md")],
        _fs_move,
    )
    archived = _read(tmp_path, "docs/sessions/history/2026-01/0001-20260101-x.md")
    assert archived == "[a](../../../architecture.md)"


def test_refusals_write_nothing(tmp_path: Path) -> None:
    names = _corpus(tmp_path, {"docs/a.md": "# A", "docs/b.md": "# B"})
    cases = [
        ([("docs/gone.md", "docs/done/gone.md")], "not a tracked document"),
        ([("docs/a.md", "docs/b.md")], "already exists"),
        ([("docs/a.md", "../outside.md")], "leaves the corpus"),
        ([("docs/a.md", "docs/a.txt")], "only markdown"),
        ([("docs/a.md", "docs/c.md"), ("docs/b.md", "docs/c.md")], "already exists"),
    ]
    for pairs, reason in cases:
        problem = move_doc.refusal(pairs, names)
        assert problem is not None and reason in problem
