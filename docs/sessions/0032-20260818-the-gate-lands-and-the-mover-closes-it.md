# 0032 · 2026-08-18 · The integrity gate lands, and the mover closes its own arc

**Scope:** the same day as 0031's close, picked up at `/recall`. The six-session-old "CI link +
encoding check" item was minted, aligned, planned, implemented, reviewed, and delivered — then a
sibling grew out of a joke ("why done/ by hand if we have the script?") and the arc closed itself:
the record mover's first real run moved 0127's ticket and RFC, and then its own ticket, into
`done/`.

## Work done

- **`/recall` → `/to-tickets`** — the docs-integrity gate minted at position 0127 (nearest free
  slot; 0121–0126 left no integer) after a three-question align: pytest guard tests as the
  vehicle, history-exempt outbound links, worked ahead of 0121.
- **`/plan-impl`, two validation passes** — the plan was built from a full-corpus scan rather than
  the ticket's premise, which inverted two assumptions: the live corpus was already clean (zero
  broken links or anchors), and a **fourth live byte defect existed** — `.cursorignore` was
  UTF-16 LE. The second pass added the symlink-materialization nuance, the close-moment exemption
  edge, and the ATX-only/setext limits, each claim produced by the command that verifies it.
- **An adjacent-scope `/align`** folded everything into 0127 under a no-overengineering razor:
  invisible-codepoint blocklist (not a category scan), the session-link ban, code-pointer
  resolution with **one canonical repo-root citation form**, queue↔folder agreement, session
  filename↔H1 identity. Dropped with reasons: grammar policing, row-vs-header text, rolling-window
  timeliness (time turns a green tree red).
- **`/implement`** — three files in the guard idiom: shared
  [docs_corpus.py](../../tests/deterministic/docs_corpus.py) primitives, the
  [integrity guard](../../tests/deterministic/test_docs_integrity_guard.py), the
  [conventions guard](../../tests/deterministic/test_docs_conventions_guard.py); a 23-site
  citation sweep (including `normalization.py`'s outright wrong relative path); `.cursorignore`
  re-encoded. **First live run caught real drift**: `done/01-0030.0020` had closed with all eight
  acceptance boxes unchecked.
- **`/review-impl`** — six findings, all applied: two code-side (self-pin floor raised to the
  RFC's measured 1,000; session-ban tightened to the exact README path), four doc-side grooms.
- **0128 minted and implemented in one stretch** — the
  [mechanical record mover](../tickets/done/01-0128-mechanical-record-moves.md) at
  `.agents/scripts/move_doc.py`: batch pairs, refusal-or-nothing, prose-identical rewrites, live
  citers only. Its acceptance instrument is the gate itself.
- **The bootstrap close** — one batch invocation moved 0127's ticket + RFC and 0128's own ticket;
  the guards proved the move. 362 → **402 tests**, pyright clean, ruff clean.

## Settled this session

- **Documentation integrity is CI-gated** — links/anchors, bytes, invisibles, code pointers,
  queue agreement, session identity; exemption policy and incident history →
  [cicd.md](../cicd.md#ci-pipeline), [0127 (done)](../tickets/done/01-0127-docs-integrity-gate.md).
- **Code comments cite docs in one canonical repo-root form** (`docs/edge/provider.md`), machine
  enforced; the mixed styles had already produced a silently wrong path →
  [RFC 0127 (done)](../rfc/done/01-0127-docs-integrity-gate.md) § 2.
- **Dated records are link-exempt as a *set* that includes dreams; a README inside an exempt
  directory stays gated** → [0127 (done)](../tickets/done/01-0127-docs-integrity-gate.md).
- **The invisible-codepoint rule is a frozen blocklist, not a category scan** — genuinely useful
  invisibles only, per the align's razor → [RFC 0127 (done)](../rfc/done/01-0127-docs-integrity-gate.md) § 2.
- **Lifecycle moves are mechanical; a paired close goes in one batch** so each moved record cites
  the other's final home → [cicd.md](../cicd.md#ci-pipeline),
  [TICKET-FORMAT](../../.agents/skills/to-tickets/TICKET-FORMAT.md#one-basename-per-work-item),
  [0128 (done)](../tickets/done/01-0128-mechanical-record-moves.md).
- **`.agents/` is the whole non-product tooling home** — scripts beside skills, stable across the
  `.claude`/`.codex`/`.cursor` symlinks → [0128 (done)](../tickets/done/01-0128-mechanical-record-moves.md).
- **An active ticket with no boxes passes the queue guard** — a decision-bearing ticket before its
  align is a legitimate state; the drift that matters is finished-but-unmoved →
  [RFC 0127 (done)](../rfc/done/01-0127-docs-integrity-gate.md) § 2.

## Found, not settled

Nothing new was left open: the session's one standing irritant (the CI check, sixth session
running) is delivered, and RFC 0127's close-moment limitation was discharged by 0128 the same day.
Pre-existing items stand where they live — parity enforcement at
[#41](../concerns.md#41-parity-evidence-is-unenforced-and-unrouted), the v1 queue at the
[delivery status](../tickets/README.md).

## Continuation

1. **0121 — second-provider fallback**, through its own `/plan-impl`; unchanged from 0031, now
   genuinely next.
2. **`uv sync` is transiently blocked** — the running meteoscape MCP server holds the venv's
   `meteoscape.exe`, so this arc ran under `--no-sync`; resolves when that server restarts.
   Environment fact, not a defect.

## Advisory read

**What is great.** The gate started working before it existed and never stopped. Planning's scan
found the UTF-16 `.cursorignore`; the first live run found the unchecked done-ticket; the mover's
tests were corrected by the guard's own defect finder (a fixture cited an anchor its target never
declared); and the close of the very arc that built it exposed two more edges — `git mv` cannot
move a never-added record, and a directory link (`./rfc`) whose members became transitive the
moment the last active RFC left. Five catches, five different instruments, one day.

**What is good enough.** The lean cut. Every dropped check has its reason recorded in the done
ticket's Out of scope, so the next "should the gate also…" conversation starts from a written no.

**What is questionable.** The invisible-codepoint constants had to be authored as literal
invisibles twice before landing as escapes — the authoring channel converts `\uXXXX` into the real
character, which the file-editing tools then cannot reliably match. The defect class the gate
exists for reached through the tools used to build the gate; the eventual fix was a byte-level
replacement outside them. The module now states its own escape discipline in its docstring.

**What is out of balance.** Two maintenance tickets in one day against a product queue that has
been waiting since 0120 — deliberate, and worth not repeating: the toil items are delivered, and
0121 has no remaining excuse.

**Hidden edges.** A corpus rule is only as true as its checker's model of "directory" — `./rfc`
was valid for months because active RFCs existed, and the close that emptied the directory is also
the event that revealed the checker knew only immediate parents. Rules that quantify over
structure get tested by structure *changing*, not by review.

**What would make life easier.** Nothing new to ask for — this session was the answer to six
sessions of asking. The next friction will name itself at 0121.

**What next.** Commit the arc, then 0121 through `/plan-impl`.
