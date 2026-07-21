# m1 — Type contract hygiene

- **Status:** Done
- **Kind:** Maintenance — not a v1 deliverable; no product capability changes
- **Depends on:** [003a — Profile reach](./003a-profile-reach.md) (landed; contributed 2 of the 40 errors)
- **Plan:** [RFC 0004 — Separability narrowing and predicate hygiene](../../rfc/done/0004-20260721-separability-narrowing.md)
- **Outcome:** `uv run pyright` clean across `src` and `tests`, with every narrowing placed where the
  type is genuinely provable and no design contract weakened to get there.

## Parent PRD

None — this is maintenance, not v1 delivery scope. The design decisions it encodes are owned by
[ADR-0002](../../adr/0002-data-model.md) and [ADR-0007](../../adr/0007-capability-carries-its-domain.md); the
implementation plan is [RFC 0004](../../rfc/done/0004-20260721-separability-narrowing.md).

## Why now

CI runs bare `uv run pyright` with `include = ["src", "tests"]`. `tests/` reports **40 errors** (`src/`
reports none), so `main` is red. Triage found the errors are not one problem: a few are real defects
the checker caught, the rest are the `Separable` facet and the Manifold facets **working as designed**
— a test holding a base-typed value and reaching for a refinement's member.

It runs **before [003b](../003c-request-shaping.md)** because 003b is the first consumer of
`resolve_reach`, and settling how reach's geometry is typed while the resolver has no caller is
cheaper than renegotiating it once the surface depends on it.

## What to build

Four stages, detailed in [RFC 0004](../../rfc/done/0004-20260721-separability-narrowing.md):

1. **Docs** — ✅ landed in `29a50c5`: [#12](../../concerns.md#12-curvilinear-domains) split into
   curvilinear source vs target roles, [#36](../../concerns.md#36-unserved-and-uncomparable-are-indistinguishable)
   filed, ADR-0002's admission asymmetry stated.
2. **The `grid` precondition** — `GridReachRule` validates that its candidates are separable before
   comparing, and rejects with a `CompositionError` naming the producer. Removes a live
   `AssertionError` path and a misleading diagnosis.
3. **Honest return types** — four covariant narrowings on concrete implementations
   (`GridDomain.axis`, `Weaver.weave`, `OpenMeteoProvider.footprints` / `.capability`); delete the
   guard they make unreachable.
4. **Type debt sweep** — use-site narrowing where a test legitimately holds a base-typed value, plus
   fixture repair, iterated until `pyright` is clean.

## What not to build

- **No `Domain` hierarchy change.** `SeparableDomain` (a named `Domain & Separable` intersection) was
  considered and rejected: `Selection.domain`, `Coverage.domain`, and `Provider.footprints` are
  precisely where curvilinear geometry enters, so narrowing them would delete
  [#12](../../concerns.md#12-curvilinear-domains) across four signatures instead of one base class.
- **No change to `Domain.matches`.** It stays **total** — the Arbiter's degrade path depends on a
  candidate that cannot be compared returning `False` and being skipped, not raising
  ([ADR-0002](../../adr/0002-data-model.md)).
- **No `resolve_reach` return-type change.** Deciding it before 003b — its only caller — exists would
  fix a contract to a consumer that makes no demands yet.
- **No pyright config relaxation.** Excluding `tests` would hide the real defects the triage found.

## Acceptance criteria

- `uv run pyright` reports **0 errors** across `src` and `tests`.
- No `# type: ignore` is added, and the two that exist (`tests/nodes/providers/test_open_meteo.py:194`
  and `:212`) are **removed**, not carried.
- `GridReachRule` raises `CompositionError` naming the producer when handed a non-separable candidate;
  no path reaches the bare `assert` in `_split`.
- `Domain.matches` is unchanged; `tests/manifold/test_domain.py`'s
  `footprint.matches(_NonSeparable()) is False` still passes.
- No abstract contract narrows: `Provider.footprints`, `Coverage.domain`, `Selection.domain`, and
  `Capability` keep their declared types.
- `pytest` stays green and `ruff` stays clean.

## Decisions owned by this ticket

None open. The four that were live are settled in
[RFC 0004](../../rfc/done/0004-20260721-separability-narrowing.md): `matches` stays total, `resolve_reach`
keeps `-> Mapping[ParameterId, Domain]`, `OpenMeteoProvider.capability` narrows, and this ticket is
maintenance rather than a numbered deliverable.
