# Doc-corpus integrity gate — implementation plan

**Authored:** 2026-08-18
**Last amended:** 2026-08-18 (post-review groom — helper roster and self-pin floors matched to
what landed, the boxless-active-ticket allowance and the concern-ref digit cap stated; earlier
passes: the adjacent-scope align fold, symlink materialization, close-moment exemption edge,
heading/indented-code limits)

Implements [doc-corpus integrity gate](../../tickets/done/01-0127-docs-integrity-gate.md): guard tests in
the deterministic suite that fail CI on a live document's broken relative link or heading anchor,
on byte and invisible-codepoint defects in any tracked file, on unresolvable code-to-doc pointers,
and on queue↔folder disagreement.

## 1. Measured facts (2026-08-18 planning scan)

A full-corpus scan was run at planning; every claim below is measured, not assumed.

- **151 tracked markdown files**; ~2,490 relative links, 141 intra-document anchor links,
  18 directory links (e.g. `[ADRs](./adr)`), 9 external URLs, **zero reference-style link
  definitions**.
- **The live corpus is clean today**: with fence-aware extraction, 0 broken relative links and
  0 broken anchors outside the exempt directories. Every placeholder link in the
  `.agents/skills/*-FORMAT.md` docs (`./RR-NNNN-slug.md`, `{basename}`) sits inside a fenced code
  block — so format docs can be gated as-is, and the gate machine-enforces that examples stay
  fenced.
- **One historical dangler**: `docs/rfc/done/0002-…` → `.claude/skills/tdd/SKILL.md` — inside an
  exempt directory, as the ticket predicts.
- **One live byte defect**: `.cursorignore` is UTF-16 LE (`ff fe` BOM, NUL-interleaved ASCII).
  Its repair to plain UTF-8 is stage 2 work under the ticket's lands-green criterion.
- **Three tracked directory symlinks** (`.claude/skills`, `.codex/skills`, `.cursor/skills` →
  `.agents/skills`): listed by `git ls-files` but not regular files, so the byte walk skips
  non-file entries. On a Windows clone with `core.symlinks=false` git materializes a symlink as a
  regular file holding the target path — plain ASCII, so it passes the byte rule; either
  materialization is safe.
- The GitHub-style slugger below validated against all 141 intra-doc anchors and every
  cross-file `#fragment` in the corpus with zero false breaks (headings with `.`, `;`, em-dashes,
  parentheses all covered).
- *(2026-08-18 align scan)* **Zero links into `docs/sessions/`** from anywhere, and **zero
  invisible codepoints** in any tracked file — the session-link ban and the invisible blocklist
  land green. **All 53 `#NN` concern refs and all 109 `ADR-NNNN` refs in `src/`+`tests/` resolve**
  against live `concerns.md` anchors and `docs/adr/` files. The 31 `.md` mentions mix three
  citation styles; 17 resolve by basename only, including **one measured wrong path**
  (`normalization.py` → `../../../docs/parameters.md`) — the canonical-form sweep repairs all of
  them. The delivery map and ticket folders are consistent today (row ⇔ file bijection holds; the
  one active RFC pairs with its ticket).

## 2. The gate's contract

**Universe `U`** — `git ls-files -z --cached --others --exclude-standard`, taken as exact-case
strings from the repository root. Rationale: exact-case matching catches case drift that a
Windows working tree hides from an Ubuntu CI checkout, and including untracked-but-unignored
files lets a freshly minted document resolve before it is ever `git add`ed. CI (`actions/checkout`)
and any dev clone both have git; the gate does not fall back.

**Link-gated set `G`** — every `.md` in `U` **except** files under the dated-record directories:
`docs/sessions/`, `docs/tickets/done/`, `docs/rfc/done/`, and `docs/dreams/` — with one carve-out:
a `README.md` inside an exempt directory is a maintained document and stays gated
(`docs/sessions/README.md` today). Dreams were added to the ticket's exemption list at planning:
they are dated records deliberately outside the ownership table and not maintained against the
corpus ([docs/README](../../README.md)). Repo-root `README.md` and the `.agents/skills` docs are in
`G` — both are cross-referenced from `docs/` and measured clean.

**Link rule** — for each inline link `[text](target)` found outside fenced code blocks and inline
code spans in a member of `G`:

```
target starts with http(s)/mailto  →  skipped (the gate is network-free; cicd.md)
target is "#frag"                  →  frag ∈ anchors(this file)
target is a relative path[#frag]   →  normalized path ∈ U, or a directory holding members of U
   …and path ends in .md with frag →  frag ∈ anchors(target)      (done/ targets included)
   …path is not .md, frag present  →  frag ignored (GitHub line refs like #L10)
```

A reference-style link definition (`[label]: target`) anywhere in `G` **fails the gate** as
unsupported: zero exist today, and failing loudly beats silently not checking a link shape the
checker cannot see.

**Anchor slugs** — GitHub's algorithm: strip `*`/`_`/backtick formatting, lowercase, drop every
character outside `[\w\- ]`, spaces → hyphens; the n-th duplicate heading appends `-n`. Headings
inside fenced blocks do not produce anchors.

**Byte rule** — every regular file in `U` must decode as strict UTF-8, carry no BOM (UTF-8's
`ef bb bf` or any UTF-16/32 mark), and contain no C0 control character other than tab, LF, and CR.
Strict-UTF-8 decode subsumes the NUL/UTF-16 case. A binary-suffix allowlist exists and is empty;
adding a suffix to it is a reviewed change, not something the checker infers. Historical docs are
not exempt here — bytes are not prose (ticket). *(Align:)* the same walk rejects one frozen
blocklist of invisible codepoints — U+200B–200D, U+202A–202E, U+2066–2069, FEFF beyond position
zero, U+2028, U+2029, U+00A0 — a membership test, deliberately not a Unicode-category scan.

**Session-link ban** — a link from a member of `G` whose normalized target sits under
`docs/sessions/` fails unless the target is `docs/sessions/README.md`. One predicate on the
existing link walk; enforces [sessions/README](../../sessions/README.md)'s documented rule.

**Code-pointer rule** — over every `.py` in `U` under `src/` and `tests/`:

```
#NN     (two or three digits) →  matches a live `## NN.` anchor in docs/concerns.md
                                 (a settled concern's gap ⇒ failure: the dangling-premise defect;
                                 four digits reads as a ticket or session number, not a concern)
ADR-NNNN                      →  docs/adr/NNNN-*.md exists in U
<anything>.md                 →  the mention, taken verbatim, is a repo-root-relative member of U
                                 (canonical form: docs/edge/provider.md — align decision (b))
```

**Queue/record agreement** — parsed from the delivery map and ticket files: a row whose Status is
`Done` links into `done/` and only such rows do; every `docs/tickets/done/` ticket has all
acceptance boxes checked, and an active ticket that has boxes must have one open — a boxless
active ticket passes, since a decision-bearing ticket before its align legitimately carries none
yet; a session file's `NNNN-YYYYMMDD` filename agrees with the number and date in its own H1 (all
sessions, history included — the facts are static, so no time dependence enters the suite).

## 3. Code shape

Three files *(align: two guard modules + one shared helper module — the families differ in
machinery and failure mode: integrity fails as "a byte or path broke", conventions as "two
artifacts disagree")*:

- `tests/deterministic/docs_corpus.py` — shared helpers (`fakes.py` precedent): universe, code
  stripping, link extraction, anchor slugs.
- `tests/deterministic/test_docs_integrity_guard.py` — bytes, invisibles, links, anchors, the
  session-link ban.
- `tests/deterministic/test_docs_conventions_guard.py` — code pointers, queue↔folder agreement,
  session date sanity.

Both guard modules follow the established idiom ([test_store_privacy_guard.py](../../../tests/deterministic/test_store_privacy_guard.py),
[test_probe_seam_guard.py](../../../tests/deterministic/test_probe_seam_guard.py)): module docstring
names the durable owner (cicd.md § CI pipeline), and a self-pin test per module proves the guard
found something to guard. No `src/` code — this checks the repository, not the
product; nothing here is public API.

The one deliberate seam: **defect finders take `(root, names)` as parameters** instead of reading
module constants —

```
strip_code(text) / heading_anchors(text) / links(text)     shared, public in docs_corpus.py
live(name) / resolve_name(source, relpath)                 shared policy — the guards and the
                                                           record mover (0128) read one truth
_link_defects(root, names) / _byte_defects(root, names)          → [(kind, message)]
_pointer_defects / _queue_defects / _session_defects(root, names) → [message]
```

so the negative tests feed synthetic corpora from `tmp_path` through the *same* functions the
live gate runs, with no git dependency; only the live-gate tests call `git ls-files` (cwd derived
from `Path(__file__)`, as the existing guards derive `_SRC`). Defects carry file, link/byte, and
reason — the assertion message is the repair instruction.

Tests:

- Self-pins: integrity — ≥ 100 markdown files in `U`, ≥ 1,000 gated links extracted (1,267
  measured at landing); conventions — ≥ 25 concern refs, ≥ 50 ADR refs, ≥ 10 queue rows,
  ≥ 20 session records found. A guard that guards nothing passes silently.
- Integrity synthetic negatives (each proves the *reason*, not just a raise): dangling relative
  link; existing file + dangling anchor; fenced placeholder ignored; exempt-directory outbound
  ignored; `README.md` in an exempt directory still gated; reference-style definition rejected;
  link into `docs/sessions/` rejected, its README accepted; UTF-8 BOM; UTF-16 file; `\x01`
  control byte; a blocklisted invisible (e.g. U+200B); empty file passes.
- Conventions synthetic negatives: `#NN` ref to a settled concern's gap; `ADR-NNNN` with no file;
  `.md` mention that is not repo-root-canonical; a `Done` row linking outside `done/`; a `done/`
  ticket with an open box; an active ticket with none; a session H1 date disagreeing with its
  filename.
- Live gates: `test_live_links_resolve`, `test_live_anchors_resolve`, `test_bytes_are_clean`,
  `test_code_pointers_resolve`, `test_queue_and_folders_agree`, `test_session_records_dated`.

## 4. Stages

Per /tdd, red→green inside each stage; the suite is green at every stage boundary.

1. **Checker + synthetic proof.** Write the helpers and the full synthetic-negative set red-first
   against `tmp_path` corpora, then implement to green. No live-corpus assertion yet, so the tree
   stays green throughout.
2. **Integrity live gate + first catch.** Repair `.cursorignore` to plain UTF-8 *first*, then add
   the integrity live-gate tests and self-pin — order chosen so the gate's first run over the tree
   is green, per the ticket's lands-green criterion. (Flipping the order would commit a red test;
   nothing depends on the UTF-16 encoding — the file is line-oriented ASCII patterns either way.)
3. **Conventions module + citation sweep.** Red-first synthetic negatives for the conventions
   checks, implement to green; then the one-time sweep of `.md` citations in `src/`+`tests/` to
   the canonical `docs/…` form (~30 sites, `normalization.py`'s wrong path among them); then the
   conventions live gates and self-pin. Same repair-before-gate ordering as stage 2.
4. **Docs landing.** Rewrite [cicd.md](../../cicd.md#ci-pipeline)'s "not gated" paragraph to state
   the gate and its exemption policy, linking the ticket; check the ticket's boxes; flip the queue
   row. Close-out (done/ moves) follows the standard ticket lifecycle.

## 5. Acceptance-criteria mapping

| Ticket criterion | Proven by |
|---|---|
| Dangling link / dangling anchor fails, pinned by negative tests | stage 1 synthetic set |
| The routine move is caught from both sides | both sides reduce to the dangling-link negative — a stale inbound citer and a mis-depthed outbound link break identically |
| Exempt dirs don't gate, zero allowlist entries | exempt-dir negative + live gate green over the one measured historical dangler |
| BOM / control char fails anywhere, historical included | BOM, UTF-16, `\x01` negatives + live byte gate over all of `U` |
| Inside the existing CI pytest step, network-free | modules live under `tests/deterministic/` (`testpaths`); external URLs skipped by rule |
| First-run violations repaired in the same change | `.cursorignore` re-encoded (stage 2); citation sweep (stage 3) |
| Invisible blocklist fails, pinned | U+200B negative + live byte gate, stages 1–2 |
| Session-link ban | rejected/accepted negative pair, stage 1 |
| Code pointers: settled concern / missing ADR / non-canonical `.md` fail | conventions negatives + `test_code_pointers_resolve`, stage 3 |
| Queue↔folder and session-date agreement fail on mismatch | conventions negatives + live gates, stage 3 |
| cicd.md rewritten at landing | stage 4 |

## 6. Limitations and follow-ups

- **Fence handling is a line-toggle** (``` and ~~~); no nested or four-backtick fence awareness,
  and links inside *indented* (four-space) code blocks are still extracted. Heading recognition is
  **ATX only** (`#`) — a setext heading's anchor would read as dangling; zero setext headings
  exist (grep-verified 2026-08-18). All acceptable: validated against the full corpus with zero
  misreads, and every misread fails *loud* (a false break naming the file), never silent.
- **A record's outbound links go ungated at the moment it moves into an exempt directory** — the
  close-out convention still owes the re-depth of the moved file's own links, and only the inbound
  half (every live citer) plus the byte half (where the historical `\x01` injection happened) are
  machine-checked. The exemption policy buys this deliberately; the alternative was a per-file
  allowlist, rejected at the minting align. *(Discharged 2026-08-18:
  [mechanical record moves](../../tickets/done/01-0128-mechanical-record-moves.md) performs the re-depth
  itself.)*
- **External URLs are never checked** — the gate stays network-free; no follow-up owner today.
- **A live doc citing `.claude/skills/…` will fail** even though the symlink resolves on disk:
  paths under tracked symlinks are not in `U`. Deliberate — `.agents/skills` is the one canonical
  home, and the gate steers citations to it.
- **A benign `#NN` literal in a future code comment collides with the concern-ref pattern** and
  fails the gate; the remedy is rewording the comment. Accepted: concern refs are the documented
  code-pointer convention, all 53 current matches are genuine, and the failure is loud and named.
- **Parity-evidence enforcement stays out** →
  [#41](../../concerns.md#41-parity-evidence-is-unenforced-and-unrouted) (ticket's non-decision).
- **Dropped at the align as not worth machine enforcement**: status-vocabulary and
  filename-grammar policing, row-vs-header status text, RFC header grammar, rolling-window
  timeliness (time-dependent) — recorded in the ticket's Out of scope.
- No temporary code is introduced; nothing here needs a dissolution TODO.
