# Doc-corpus integrity gate

- **Status:** Done
- **Type:** AFK
- **Kind:** Maintenance
- **Plan:** [Doc-corpus integrity gate RFC](../../rfc/done/01-0127-docs-integrity-gate.md) — the guard-test
  module split (two guards + shared helpers), the git-derived file universe, the exemption set
  (dreams added), strict UTF-8 plus an invisible blocklist as the byte rule, and the canonical
  repo-root code-citation form.
- **Outcome:** CI fails when a live document's relative link or heading anchor stops resolving,
  when any tracked file carries a BOM, control character, or listed invisible codepoint, when a
  code comment's doc pointer (concern, ADR, or `.md` path) no longer resolves, or when the queue
  and the ticket folders disagree; historical records stay exempt from link gating. *(Widened
  2026-08-18 at the adjacent-scope align.)*

## Parent

[cicd.md § CI pipeline](../../cicd.md#ci-pipeline) — the "Documentation link integrity is not gated,
and should be" paragraph; this ticket closes it.

## Why reading cannot catch this

The corpus is deliberately cross-referential — one canonical home per fact, cited relatively from
everywhere else — so every routine lifecycle move (a ticket or RFC closing into `done/`, a session
aging into `history/`) re-depths every link inside the moved file and invalidates every link to it:

```
docs/tickets/01-0120-twc-provider.md      →  docs/tickets/done/01-0120-twc-provider.md

inside the moved file:  ../concerns.md#49  must become  ../../concerns.md#49
in every live citer:    ./01-0120-…md      must become  ./done/01-0120-…md
```

The check has been manual at landing time — skipped exactly when a session runs long — and three
defect classes have already slipped past both `grep` and human reading, each caught only by an
ad-hoc program: a UTF-8 BOM in `src/` that broke the store-privacy guard, four ticket links broken
by a `done/` move, and 59 invisible `\x01` characters injected by a re-depth repair pass. Reading
cannot see bytes; only a gate can.

Historical records are the deliberate wrinkle: sessions and completed tickets/RFCs are kept as
written, so later moves make their outbound links dangle *legitimately*. A blanket checker would
either fail forever or invite blanket suppression.

## What to build

Guard tests in the deterministic suite (`tests/deterministic/`) — the repo's idiom for
machine-enforcing an invariant, riding the existing `uv run pytest` CI step so no new pipeline
surface appears. Vehicle, exemption policy, and queue slot were decided at minting (2026-08-18).
Three checks:

- **Link + anchor resolution over live docs.** Every relative markdown link in a live document must
  resolve to an existing file, and a `#fragment` must match a real heading in the target
  (GitHub-style slugs). File-existence-only checking is insufficient: an anchor is how a fact is
  cited, and losing one is the silent structural loss the gate exists to catch.
- **History exemption, by directory.** `docs/sessions/`, `docs/tickets/done/`, `docs/rfc/done/`,
  and `docs/dreams/` (*dreams added 2026-08-18 at planning: dated records deliberately outside the
  ownership table, not maintained against the corpus —* [docs/README](../../README.md)) are exempt
  from *outbound* link gating — those records are kept as written and their danglers are
  legitimate. A `README.md` inside an exempt directory is maintained and stays gated. Inbound
  links to them from live docs are still gated (a live doc citing a moved record must carry the
  `done/` segment).
- **Byte hygiene, everywhere.** No UTF-8 BOM and no C0 control characters other than tab, LF, and
  CR in any git-tracked text file — `src`, `tests`, `docs`, and workflow files alike. Historical
  docs are *not* exempt here; bytes are not prose. *(2026-08-18 align:)* the same rule bans a short
  blocklist of invisible codepoints with a real damage record — zero-widths U+200B–200D, BiDi
  controls U+202A–202E and U+2066–2069, FEFF beyond position zero, U+2028/2029, NBSP.
- **Session-link ban** *(added 2026-08-18 align)*. No gated document links to anything under
  `docs/sessions/` (its `README.md` excepted) — enforcing the documented "nothing links *to* a
  session" rule ([sessions/README](../../sessions/README.md)), measured at zero violations today.
- **Cross-artifact conventions** *(added 2026-08-18 align)*. Code comments in `src/` and `tests/`
  cite docs in one canonical repo-root form (`docs/edge/provider.md`): a `#NN` concern ref must
  match a live `concerns.md` anchor (a ref to a settled concern fails — the dangling-premise
  defect), an `ADR-NNNN` ref must match a file in `docs/adr/`, and a `.md` mention must resolve
  from the repo root, exact case. The delivery map and the folders must agree: a `Done` row links
  into `done/` and vice versa; a `done/` ticket has every acceptance box checked while an active
  ticket has at least one open; a session's filename number and date agree with its own H1.

External URLs are out of scope: the CI gate is deliberately network-free
([cicd.md](../../cicd.md#ci-pipeline)).

## What this ticket does not decide

- Whether parity-evidence enforcement joins CI —
  [#41](../../concerns.md#41-parity-evidence-is-unenforced-and-unrouted)'s question, untouched here.
- Markdown style or formatting linting — this gate checks integrity, not style.

## Acceptance criteria

- [x] A live doc with a relative link to a missing file fails `uv run pytest`; a link to an
      existing file but a missing heading anchor fails the same way — pinned by negative tests
      feeding the checker synthetic violations, not by the tree happening to be clean.
- [x] The routine event is covered: a document moved without re-depthing is caught from both sides
      — the moved file's own outbound links (while it is live) and every live citer's inbound link.
- [x] Outbound links in `docs/sessions/`, `docs/tickets/done/`, `docs/rfc/done/`, and
      `docs/dreams/` (*added 2026-08-18*) do not gate: the suite is green over the tree's existing
      legitimate danglers with zero per-file allowlist entries.
- [x] A BOM or a forbidden control character in any tracked file fails the gate — historical docs
      included; each pinned by a synthetic negative test.
- [x] The gate runs inside the existing CI pytest step, network-free; no new workflow step.
- [x] Any live-doc violations the first run surfaces are repaired in the same change — the gate
      lands green.
- [x] [cicd.md](../../cicd.md#ci-pipeline)'s "not gated" paragraph is rewritten at landing to state
      the gate and its exemption policy, linking here.
- [x] *(added 2026-08-18)* An invisible-blocklist codepoint in any tracked file fails, pinned by a
      synthetic negative test.
- [x] *(added 2026-08-18)* A gated doc linking under `docs/sessions/` (README excepted) fails.
- [x] *(added 2026-08-18)* A code comment citing a settled concern, a missing ADR, or a
      non-canonical or unresolvable `.md` path fails, each pinned by a synthetic negative; the
      one-time sweep of existing citations to the canonical `docs/…` form (~30 sites, including
      one measured wrong path) lands in the same change.
- [x] *(added 2026-08-18)* A `Done` delivery-map row linking outside `done/` (or vice versa), a
      `done/` ticket with an open acceptance box, an active ticket whose every box is checked (a
      boxless ticket is a legitimate pre-align state and passes), and a session whose filename
      number or date disagrees with its H1 each fail, pinned by synthetic negatives.

## Out of scope

- External URL liveness — the gate stays network-free; no home today.
- Parity-check enforcement and routing →
  [#41](../../concerns.md#41-parity-evidence-is-unenforced-and-unrouted).
- Status-vocabulary, filename-grammar, and RFC-header policing; row-status vs header-status text
  agreement — dropped at the 2026-08-18 align as not worth machine enforcement: each is reviewed
  once at minting, and the folder-agreement checks catch the drift that matters.
- Rolling-window timeliness (a session overdue for `history/`) — time-dependent: a green tree
  would turn red by the passage of days, breaking the deterministic suite's contract.
