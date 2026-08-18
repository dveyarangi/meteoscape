"""Guard: the documentation corpus stays mechanically sound (docs/cicd.md § CI pipeline).

Live documents must link and anchor cleanly; every file in the universe must be plain UTF-8 free
of BOMs, stray control characters, and invisible codepoints. Dated records — sessions, `done/`
tickets and RFCs, dreams — are kept as written, so their *outbound* links are exempt; a README
inside an exempt directory is maintained and stays gated. Nothing links into `docs/sessions/`
beyond its README: sessions are unlinked by design.

The corpus's defect-finding instrument is reading, and reading cannot see bytes — every rule here
gates a defect class that has already slipped past review. Invisible codepoints appear below only
as escape sequences, so this module can pass its own gate.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path

from docs_corpus import (
    REPO_ROOT,
    heading_anchors,
    links,
    live,
    resolve_name,
    strip_code,
    universe,
)

_SESSIONS = "docs/sessions/"
_SESSIONS_README = "docs/sessions/README.md"
_EXTERNAL_SCHEMES = ("http://", "https://", "mailto:")
_REF_DEF = re.compile(r"^\s*\[[^\]]+\]:\s+\S+", re.MULTILINE)

_BOMS = (b"\xff\xfe\x00\x00", b"\x00\x00\xfe\xff", b"\xef\xbb\xbf", b"\xff\xfe", b"\xfe\xff")
_ALLOWED_CONTROLS = frozenset("\t\n\r")
_STRAY_BOM = "\ufeff"
_INVISIBLES = frozenset(
    "\u200b\u200c\u200d"  # zero widths
    "\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069"  # BiDi controls
    "\u2028\u2029\u00a0" + _STRAY_BOM  # line/paragraph separators, NBSP
)
_BINARY_SUFFIXES: frozenset[str] = frozenset()
"""Suffixes excused from the byte rule. Empty on purpose: adding one is a reviewed change."""


def _link_defects(root: Path, names: Sequence[str]) -> list[tuple[str, str]]:
    """(kind, message) for every broken promise a gated document's links make."""
    members = set(names)
    directories: set[str] = set()
    for name in members:  # every ancestor: a directory link may reach members only transitively
        parts = name.split("/")[:-1]
        for depth in range(1, len(parts) + 1):
            directories.add("/".join(parts[:depth]))
    anchors: dict[str, set[str]] = {}

    def anchors_of(name: str) -> set[str]:
        if name not in anchors:
            anchors[name] = heading_anchors((root / name).read_text(encoding="utf-8"))
        return anchors[name]

    defects: list[tuple[str, str]] = []
    for name in sorted(n for n in members if live(n)):
        text = (root / name).read_text(encoding="utf-8")
        if _REF_DEF.search(strip_code(text)):
            defects.append(("ref-def", f"{name}: reference-style link definition (unsupported)"))
        for target in links(text):
            if target.startswith(_EXTERNAL_SCHEMES):
                continue
            if target.startswith("#"):
                if target[1:] not in anchors_of(name):
                    defects.append(("anchor", f"{name}: {target} names no heading"))
                continue
            path, _, fragment = target.partition("#")
            resolved = resolve_name(name, path)
            if resolved.startswith(_SESSIONS) and resolved != _SESSIONS_README:
                defects.append(("session-link", f"{name}: {target} links a session record"))
                continue
            if resolved not in members:
                if resolved not in directories:
                    defects.append(("link", f"{name}: {target} does not resolve"))
                continue
            if fragment and resolved.endswith(".md") and fragment not in anchors_of(resolved):
                defects.append(("anchor", f"{name}: {target} names no heading in the target"))
    return defects


def _byte_defects(root: Path, names: Sequence[str]) -> list[tuple[str, str]]:
    """(kind, message) for every file whose bytes lie to a reader. No document is exempt."""
    defects: list[tuple[str, str]] = []
    for name in sorted(names):
        path = root / name
        if not path.is_file():  # git-tracked symlinks materialize as directories on some setups
            continue
        if "." in name and name.rsplit(".", 1)[-1] in _BINARY_SUFFIXES:
            continue
        data = path.read_bytes()
        if data.startswith(_BOMS):
            defects.append(("bom", f"{name}: begins with a byte-order mark"))
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as error:
            defects.append(("encoding", f"{name}: not UTF-8 ({error.reason} at {error.start})"))
            continue
        controls = {c for c in text if ord(c) < 0x20 and c not in _ALLOWED_CONTROLS}
        if controls:
            listed = ", ".join(f"0x{ord(c):02x}" for c in sorted(controls))
            defects.append(("control", f"{name}: control characters {listed}"))
        invisibles = {
            c for i, c in enumerate(text) if c in _INVISIBLES and not (i == 0 and c == _STRAY_BOM)
        }
        if invisibles:
            listed = ", ".join(f"U+{ord(c):04X}" for c in sorted(invisibles))
            defects.append(("invisible", f"{name}: invisible codepoints {listed}"))
    return defects


# --- synthetic corpora: every rule proven by the reason it fires, through the live functions ---


def _corpus(tmp_path: Path, files: dict[str, str | bytes]) -> list[str]:
    for name, content in files.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content, encoding="utf-8")
    return sorted(files)


def _kinds(defects: list[tuple[str, str]]) -> set[str]:
    return {kind for kind, _ in defects}


def test_dangling_link_is_reported(tmp_path: Path) -> None:
    names = _corpus(tmp_path, {"docs/a.md": "[gone](./missing.md)"})
    (defect,) = _link_defects(tmp_path, names)
    assert defect[0] == "link" and "does not resolve" in defect[1]


def test_dangling_anchor_is_reported(tmp_path: Path) -> None:
    names = _corpus(
        tmp_path, {"docs/a.md": "[b](./b.md#real)\n[bad](./b.md#gone)", "docs/b.md": "# Real"}
    )
    (defect,) = _link_defects(tmp_path, names)
    assert defect[0] == "anchor" and "#gone" in defect[1]


def test_intra_document_anchor_is_checked(tmp_path: Path) -> None:
    names = _corpus(tmp_path, {"docs/a.md": "# Here\n[ok](#here)\n[bad](#there)"})
    (defect,) = _link_defects(tmp_path, names)
    assert defect[0] == "anchor" and "#there" in defect[1]


def test_fenced_example_links_are_ignored(tmp_path: Path) -> None:
    names = _corpus(tmp_path, {"docs/a.md": "```md\n[x](./RR-NNNN-slug.md)\n```\n`[y](./no.md)`"})
    assert _link_defects(tmp_path, names) == []


def test_directory_links_resolve(tmp_path: Path) -> None:
    names = _corpus(tmp_path, {"docs/a.md": "[adr](./adr)", "docs/adr/0001-x.md": "# X"})
    assert _link_defects(tmp_path, names) == []


def test_directory_links_resolve_through_deeper_members_only(tmp_path: Path) -> None:
    names = _corpus(tmp_path, {"docs/a.md": "[rfc](./rfc)", "docs/rfc/done/0001-x.md": "# X"})
    assert _link_defects(tmp_path, names) == []


def test_exempt_directory_outbound_links_are_ignored(tmp_path: Path) -> None:
    names = _corpus(
        tmp_path,
        {
            "docs/tickets/done/01-0001-old.md": "[legitimately dangling](../../gone.md)",
            "docs/dreams/2026-01-01-a-dream.md": "[also fine](./nowhere.md)",
        },
    )
    assert _link_defects(tmp_path, names) == []


def test_readme_inside_exempt_directory_stays_gated(tmp_path: Path) -> None:
    names = _corpus(tmp_path, {"docs/sessions/README.md": "[bad](../gone.md)"})
    (defect,) = _link_defects(tmp_path, names)
    assert defect[0] == "link"


def test_session_links_are_banned_and_its_readme_is_not(tmp_path: Path) -> None:
    names = _corpus(
        tmp_path,
        {
            "docs/a.md": "[no](./sessions/0001-20260101-x.md)\n[yes](./sessions/README.md)",
            "docs/sessions/0001-20260101-x.md": "# 0001",
            "docs/sessions/README.md": "# Sessions",
        },
    )
    (defect,) = _link_defects(tmp_path, names)
    assert defect[0] == "session-link" and "0001" in defect[1]


def test_reference_style_definitions_are_rejected(tmp_path: Path) -> None:
    names = _corpus(tmp_path, {"docs/a.md": "[label]: ./b.md\n", "docs/b.md": "# B"})
    (defect,) = _link_defects(tmp_path, names)
    assert defect[0] == "ref-def"


def test_utf8_bom_is_reported(tmp_path: Path) -> None:
    names = _corpus(tmp_path, {"a.py": b"\xef\xbb\xbfx = 1\n"})
    assert _kinds(_byte_defects(tmp_path, names)) == {"bom"}


def test_utf16_file_is_reported(tmp_path: Path) -> None:
    names = _corpus(tmp_path, {"notes.txt": "docs\n".encode("utf-16")})
    kinds = _kinds(_byte_defects(tmp_path, names))
    assert "bom" in kinds and "encoding" in kinds


def test_control_character_is_reported(tmp_path: Path) -> None:
    names = _corpus(tmp_path, {"docs/a.md": b"fine\x01text\n"})
    (defect,) = _byte_defects(tmp_path, names)
    assert defect[0] == "control" and "0x01" in defect[1]


def test_invisible_codepoint_is_reported(tmp_path: Path) -> None:
    names = _corpus(tmp_path, {"docs/a.md": "zero\u200bwidth\n"})
    (defect,) = _byte_defects(tmp_path, names)
    assert defect[0] == "invisible" and "U+200B" in defect[1]


def test_historical_documents_are_not_byte_exempt(tmp_path: Path) -> None:
    names = _corpus(tmp_path, {"docs/sessions/0001-20260101-x.md": "bidi\u202etext\n"})
    (defect,) = _byte_defects(tmp_path, names)
    assert defect[0] == "invisible"


def test_ordinary_prose_and_empty_files_pass(tmp_path: Path) -> None:
    names = _corpus(tmp_path, {"docs/a.md": "em — dash · dot ⚠\ttab\n", "empty.md": ""})
    assert _byte_defects(tmp_path, names) == []


# --- the live gates ---


def test_corpus_is_discovered() -> None:
    """A guard that guards nothing passes silently — pin that it found the real corpus."""
    names = universe(REPO_ROOT)
    documents = [n for n in names if n.endswith(".md")]
    assert len(documents) >= 100, "markdown corpus went missing"
    total_links = sum(
        len(links((REPO_ROOT / n).read_text(encoding="utf-8"))) for n in documents if live(n)
    )
    assert total_links >= 1000, "gated documents stopped carrying links"


def test_live_links_resolve() -> None:
    defects = [d for d in _link_defects(REPO_ROOT, universe(REPO_ROOT)) if d[0] != "anchor"]
    assert not defects, "\n".join(message for _, message in defects)


def test_live_anchors_resolve() -> None:
    defects = [d for d in _link_defects(REPO_ROOT, universe(REPO_ROOT)) if d[0] == "anchor"]
    assert not defects, "\n".join(message for _, message in defects)


def test_bytes_are_clean() -> None:
    defects = _byte_defects(REPO_ROOT, universe(REPO_ROOT))
    assert not defects, "\n".join(message for _, message in defects)
