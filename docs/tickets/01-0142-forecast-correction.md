# Forecast correction

- **Status:** Planned (own align precedes; opens only on stable measured bias)
- **Type:** HITL
- **Depends on:** [correction calculator](./01-0140-correction-calculator.md) (supplies the measured
  bias and the stability criteria that license correcting at all)
- **Trigger:** 0140's measured bias shown stable by the criteria 0140's align declares. Correcting an
  unmeasured or unstable bias is unfalsifiable, so this ticket does not start before that evidence
  exists.
- **Outcome:** A requested parameter can be served as a bias-corrected value, carrying synthetic
  provenance that records the correction's lineage and method, so a caller can tell a corrected value
  from a raw one and audit what produced it.

## Parent

[v1 requirements](../v1-requirements.md) — the Goal's "corrects for the measured bias", the agent's
story about telling a corrected value from a raw one, and the release criterion that correction be
validated rather than merely computed. Carved out of the
[correction calculator](./01-0140-correction-calculator.md), which delivers the bias *report* and
scopes correction out as the follow-on. Its durable product context is the
[local-station validation and bias-correction roadmap](../product-roadmap.md#priority-candidate-after-v1-local-station-validation-and-bias-correction).

## Why this is a separate ticket

0140 answers *how wrong is this source*. This answers *serve me the corrected value*. They are
separated by evidence, not by size: 0140's own scope note is that correcting an unstable bias is
unfalsifiable, so the gate between them is empirical and cannot be collapsed by planning.

The split also isolates the release's one **contract change**. 0140 produces a report; this produces a
*served parameter* whose origin is not any single upstream — which is exactly what
[ADR-0003](../adr/0003-provenance-and-origin.md) calls a **synthetic origin**, minted by a
method-bearing derivation regardless of parent count. v1 lists origin synthesis as in-scope for the
first time; this is the ticket that spends it.

## What to build

A Calculator that serves a corrected view of a provider-served parameter by applying 0140's measured
bias, with provenance that records the correction rather than impersonating its input.

- **The corrected value is a distinct product, not a silent replacement.** A caller asking for the
  raw parameter gets the raw parameter; correction is selected, never applied behind the caller's
  back. How it is selected — a distinct `ParameterId`, a profile-level declaration, or a request
  flag — is this ticket's align.
- **Provenance is synthetic and carries the method.** The lineage names the corrected source, the
  bias product, and the stations and period that bias came from. The edge serializer stops being
  pinned to the atomic-origin path.
- **`expiration` is the min over the parents** per
  [ADR-0003](../adr/0003-provenance-and-origin.md) — a correction is no fresher than the forecast it
  corrects.
- **Refusing to correct is a valid answer.** Where the bias is unmeasured, stale, or fails the
  stability criteria, the corrected parameter is unserved rather than served uncorrected — otherwise
  a caller cannot tell which they got.

## Decisions this ticket's align owns

- **How a caller asks for correction** — distinct parameter id, profile declaration, or request flag.
  Each lands differently at the edge and in `Capability`, and the choice decides whether correction is
  visible in the narrated envelope.
- **What the correction actually is** — a lead-time-dependent offset, a single scalar per
  station/parameter, or an interpolated field between stations. 0140's bias product shape constrains
  this but does not settle it.
- **How a station-located bias reaches a requested point** that is not a station — the same question
  the [Mongo obs source](./01-0124-mongo-obs-source.md) settles for observations, and the answer
  should not diverge from it.
- **Whether the stability criteria are enforced in code or by the operator** — a runtime gate that
  withholds correction, versus a documented precondition on enabling it.

## Acceptance criteria

- [ ] A requested corrected parameter returns bias-corrected values over a window at a location the
      bias product covers.
- [ ] The response distinguishes corrected from raw: provenance is synthetic and names the corrected
      source, the bias product, and the stations and period behind it — pinned by asserting the
      serialized provenance shape, not by inspecting the calculator.
- [ ] A caller asking for the raw parameter still receives raw values, unchanged.
- [ ] Where bias is unmeasured, stale, or fails the stability criteria, the corrected parameter is
      **unserved**, never silently served uncorrected.
- [ ] Corrected values are checked against the operator's existing analysis through an independent
      parity reference, within the tolerance 0140's align declared — this is the instrument for
      [v1 requirements](../v1-requirements.md)' "correction is validated, not merely computed".
- [ ] `expiration` on a corrected parameter is no later than that of the forecast it corrects.

## Out of scope

- **Measuring bias** — [correction calculator](./01-0140-correction-calculator.md).
- **Charts and presentation** — embedder-owned per the roadmap's division of labor.
- **Cross-run forecast folding** → [#9](../concerns.md#9-cross-run-combination).
- **Correcting parameters outside 0140's first slice** (temperature, relative humidity) — widening
  follows the same evidence gate, per parameter.

## Parent scope addressed

- [v1 requirements](../v1-requirements.md): the Goal's "corrects for the measured bias", the agent's
  corrected-value provenance story, and "correction is validated, not merely computed".
