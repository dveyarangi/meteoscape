# 0020 · 2026-08-04 · m4 review, stage 6, and the landing

**Scope:** code review of the m4 implementation (Cursor-authored) against its ticket / RFC / edge
record, the missing stage 6 written, live parity run, the Probe seam guard, the doc landing
(`/sync-arch` + two `/denoise` passes), and m4 moved to `done/`.

## Work done

- **Reviewed the m4 diff** (~2 200 insertions) against
  [RFC 0009](../../../rfc/done/0009-20260725-m4-snapped-t-request-mode.md) and
  [edge/provider.md](../../../edge/provider.md). The load-bearing acceptance criterion held: the leaf
  carries no mode code, no snap arithmetic outside `RegularAxis.clip`, no `SnappedAxis` import.
  Findings were doc-side or missing-stage, not algebra defects; each fix below names the doc gap
  that caused the code weirdness where there was one.
- **Wrote stage 6** ([test_e2e_forecast.py](../../../../tests/deterministic/test_e2e_forecast.py)): a
  snapped Selection through `Gateway.resolve` on a mixed direct+derived request, and the
  **divergence pin** — two fetches of one request answered with different reaches →
  `RuntimeFailure` on the Arbiter's closed-projection check.
- **Ran live parity** — green, unchanged: the last acceptance criterion.
- **Wrote the Probe seam guard**
  ([test_probe_seam_guard.py](../../../../tests/deterministic/test_probe_seam_guard.py)) — static AST,
  not import-based, since a vendor module legitimately imports the wrapper. Verified it fires by
  injecting both violation kinds, then reverting.
- **Doc landing** per the RFC's stage-6 list: ADR-0002 (`clip` on the universal axis surface,
  `SnappedAxis` as `ContinuousAxis`'s request subclass, *snapped-to as a consequence*,
  `SelectionDomain`/`ground`/`agreed_geometry`), ADR-0001 (names `ground`), ADR-0004
  (mode-dependent admission), architecture (§Provider off `Normalizer`, §Request modes),
  glossary (*Ground*, *Clip*, *SnappedAxis*; *Normalizer* → *Normalization*, a role with no
  object), edge record → `Normative` with all m4 markers cleared.
- **Two `/denoise` passes** (topic, then whole-project): stale tense in concerns #13/#20/#30,
  `Normalizer` remnants swept from v1-requirements/parameters/ADR-0006, ticket references removed
  from core docs (ADR-0002, ADR-0006, architecture, glossary), architecture's wrapper paragraph
  reduced to summary + pointer, and RFC 0009 decision 3's recorded follow-up discharged — the
  triple-verbatim `matches` fold is now `_admits_per_axis` in `domain.py`.
- **Landed m4**: ticket + RFC 0009 → `done/` with ~35 inbound links rewritten; 003c and 011
  flipped **Ready**; [delivery status](../../../tickets/README.md) updated.

Gate at close: 209 deterministic tests, live parity, ruff, ruff format, pyright — all green; full
docs link scan clean.

## Settled this session

- **`ground` returns `EnumerableDomain` and v1 wrappers narrow past it to `GridDomain`** — chosen
  over widening `EnumerableDomain` with `axis()`; recorded in
  [ADR-0002](../../../adr/0002-data-model.md) ("what ground returns") and the edge record's Resolution
  properties.
- **The post-fetch `agreed_geometry` fold is a law, structurally unfirable in the timeline shape**
  (one delivery → one lattice stamped on every record) — the edge record's Resolution section and
  Invariants say so plainly, and name the Arbiter as what actually catches cross-fetch divergence.
- **"Shorter is honest" is mode-split**: snapped asks ground against the delivery (nothing to fall
  short of); an exact ask meeting a short delivery is a `RuntimeFailure` — edge record Response +
  Outcomes.
- **The Probe seam is guarded structurally** — two rules (no manifold-type imports module-wide; no
  references inside `*Probe` bodies, `Clock` included) — edge record Invariants, *validated by*.
- **Stage 6's divergence exposure is pinned, not handled** — decision 11 confirmed by test;
  ownership unchanged (003c's landing, revisited at
  [#30](../../../concerns.md#30-response-membership-under-runtime-degraded-fallback)).
- **m4 is Done** — [ticket](../../../tickets/done/01-0100-snapped-t-request-mode.md), all six acceptance
  boxes ticked.

## Open questions

All owned elsewhere; none minted here:

- **Parity-existence is the edge record's one remaining ⚠ unguarded promise** →
  [#41](../../../concerns.md#41-parity-evidence-is-unenforced-and-unrouted).
- **RFC 0008 must be re-staged against the landed mode before 003c implementation** — recorded in
  the [003c ticket](../../../tickets/done/01-0110-request-shaping.md) status; the RFC planned the superseded
  edge-clamp.
- **Two request representations** → [#42](../../../concerns.md#42-two-request-representations-so-resolution-cannot-be-a-method)
  (triggers: 006's refill, 003c's edge migration, #39's builder).
- **Divergent winner domains go live at 003c** — its ticket carries the landing risk.

## Continuation

- **Next per the queue: 003c (request shaping) or 011 (Visual Crossing)** — both Ready, no
  ordering constraint between them. 003c starts by re-staging RFC 0008; 011 is the first real test
  of *declaration, not gate* and of the new seam guard.
- The shortfall-padding site ([#30](../../../concerns.md#30-response-membership-under-runtime-degraded-fallback))
  and the `agreed_geometry` naming checkpoint (edge record, at 006) remain future work as recorded.
