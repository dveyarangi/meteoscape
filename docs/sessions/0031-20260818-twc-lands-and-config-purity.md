# 0031 · 2026-08-18 · TWC lands as primary; the config-purity invariant

**Scope:** everything since 0030 — the late-2026-08-17 spanning-window pass (which had no record),
then 2026-08-18 end to end: two `/plan-impl` validation passes with a `/denoise` between them, a
ten-finding user review of the plan, the vendor-config-purity correction, the external
implementation landing, two `/review-impl` passes, `/sync-arch`, the live parity run, and the
ticket's close-out into `done/`.

## Work done

- **The spanning-window pass (late 08-17, previously unrecorded)** settled how the priority flip
  meets a window wider than the primary: concern #49 minted, ADR-0004 amended, the ticket's
  admission-only account corrected.
- **`/plan-impl` pass over 0120 found the plan could not boot**: `Settings` importing its defaults
  from `twc.py` while the leaf imports `StoreSpec` from config is a circular `ImportError`. The
  first fix moved the defaults *into* config — and the user rejected it as an architecture
  violation, which it was: the cycle had been the architecture objecting. The correction became the
  **vendor-config-purity invariant** (below). The same passes re-verified the composition fold
  live (all six pairs compose at every clock phase; the 12 h default refuses exactly the two
  under-long offerings) and found the pre-#49 sentence surviving in a fourth home.
- **`/denoise` found ADR-0002 still teaching the measured-false cadence-guard justification**
  ADR-0003 had corrected — fall-behind blindness instead of spend governance — contradicting the
  predicate bullet directly above it; the same account was in `cadence.py`'s comment. Both fixed;
  five ticket references purged from ADRs; session 0026 archived.
- **A ten-finding user review of the plan**: eight real (a settled-vs-provisional
  `publication_latency` contradiction, spanning pins missing from the ticket AC, stage-5 still
  told to discover confirmed `max_lead` values, an "exactly three" sweep enumeration measured
  false under its own prescribed grep, architecture.md's admission sentence predicting the wrong
  tail outcome, and three leftovers), two defended (validity checks belong in `build` because
  `OfferingDef.settings` is untyped by design and the direct path bypasses `Settings`).
- **Implementation landed externally** — the closest match of the release: `twc.py` is
  declarations plus one query builder and one envelope parse, zero algebra. 362 deterministic
  tests (+27), pyright clean. Review found grooms, not drift; among them one real catch — `.env`
  was not gitignored while `Settings` reads it.
- **Parity ergonomics converged in three steps** (profile `.env` → rejected; a runner script →
  rejected; a `--twc-api-key` pytest option → landed): the operator's key never touches a file,
  and the harness scrubs it from all evidence.
- **Live parity passed on the first attempt** — `Exact()` agreement on four parameters, 1e-6 on
  wind through independent trig + unit conversion; the only possible guard on `units=m`.
- **Stage 6 closed 0120 into `done/`** with both moves' links re-depthed and machine-verified,
  all three ⚠ markers flipped to *validated-by*, and the delivery status advanced. A second
  `/review-impl` swept comments and TODOs: the last ticket-number reference in any code comment
  is gone; every code pointer now targets an ADR, an edge record, or a concern.
- **A user `/denoise` pass** over the doc stack reviewed clean: zero broken links in live docs,
  every load-bearing rule intact, evolution dates trimmed into history's ownership.

Footprint: ~250/-70 in `src` and `tests` (+27 tests, 362 green) against a much larger doc stack —
the whole arc lands as one uncommitted pile concluded here.

## Settled this session

- **v1 always serves the primary's shape; max-reach is unbuilt policy** — the retention flow opens
  T before selection, so no ordering policy can see the window →
  [#49](../concerns.md#49-spanning-asks-serve-the-primary-max-reach-is-unbuilt-policy),
  [ADR-0004](../adr/0004-producer-resolution-and-capability.md),
  [architecture.md](../architecture.md) (admission corollary).
- **Provider-specific configuration never extends core config** — vendor defaults, vocabulary,
  and semantics live in the plugin; a plugin can register a manifest but never add a `Settings`
  field → [edge/provider.md](../edge/provider.md) invariant (guarded by
  `test_config_imports_nothing_from_nodes`), [ADR-0005](../adr/0005-build-time-composition.md).
- **The manifest names its own `default_offering`; an omitted `OfferingDef.name` resolves to it
  at the binder before the expand path** — Open-Meteo's `best_match` left `Settings` in the same
  stroke → [ADR-0005](../adr/0005-build-time-composition.md),
  [composition.py](../../src/meteoscape/nodes/composition.py).
- **The two vendor-named `Settings` fields are acknowledged v1 plumbing, dissolved at 0123** —
  along with whether the profile enumeration itself becomes declared data →
  [0123](../tickets/01-0123-config-secrets-degrade.md) (scope + acceptance criterion).
- **The cadence guard's justification is spend governance and `exp` honesty in every home** —
  ADR-0002's corollary and `cadence.py`'s comment no longer teach the fall-behind account →
  [ADR-0002](../adr/0002-data-model.md), [ADR-0003](../adr/0003-provenance-and-origin.md).
- **`publication_latency = 0` is entailed by the bucket regime, not provisional** — a live fetch
  cannot measure a delay that does not exist →
  [0120 (done)](../tickets/done/01-0120-twc-provider.md).
- **The parity key rides `--twc-api-key` (or the env var), never a file**; `.env` is gitignored →
  [tests/parity/conftest.py](../../tests/parity/conftest.py),
  [RFC 0120 stage 5 (done)](../rfc/done/01-0120-twc-provider.md).
- **0120 delivered; m4's shape/vendor split held on its second vendor** →
  [delivery status](../tickets/README.md), [edge/provider.md](../edge/provider.md).

## Continuation

1. **0121 — second-provider fallback** is next and its motivation is now live: a metered
   primary's 429 sits on the default path and fails the whole request. Plan it first.
2. **The CI link + encoding check** — sixth session running, still unticketed
   → [cicd.md](../cicd.md#ci-pipeline). This session alone ran three hand-rolled link loops, and
   the moved `done/` records now legitimately dangle from older historical docs, which only a
   mechanical check with a history-aware exclusion list can police.
3. **The `/commit` of this whole arc** — code and docs describe each other (the `cadence.py`
   comment and the RFC's account of it, the moved records and their inbound links), so the stack
   must not be split mid-description.

## Advisory read

**What is great.** The user's config-purity catch turned a mechanical fix into an architectural
invariant with a guard test — the circular import was the architecture *objecting*, and the final
shape (manifest-owned defaults, binder resolution) is strictly better than either failed attempt.
And the implementation itself: the ticket's own success criterion was "declarations plus a Probe,
nothing else," and that is what landed, first parity attempt green.

**What is good enough.** The validation-pass cadence — plan, denoise, plan again, user review —
converged: each pass found a different defect class, and the implementation review found only
grooms.

**What is questionable.** The amend-misses-its-neighbor defect dominated the stretch: roughly nine
instances across five artifacts, three authored by the amender of the previous one. Every
correction pass now ends with a neighbor sweep by grep, and that discipline caught real instances
— but it is a habit, not a mechanism.

**What is out of balance.** Two classes of self-inflicted error shared a root: claims authored
without running the claim. "Exactly three" was written from a grep that didn't match the
prescribed spelling; a full conversation of amendments carried the previous day's date. Both were
caught by the user, not the process. A measured claim in a criterion is load-bearing and must be
produced by the exact command the criterion prescribes.

**Hidden edges.** A pytest option is a smaller, better secret channel than either a config file or
a wrapper script — the third design was found only because the first two were rejected. The
lesson generalizes: operator-ergonomics seams deserve the same option-enumeration as
architectural ones.

**What would make life easier.** The CI check. Sixth session. It is the only continuation item
that has outlived every other item on every list it appeared on.

**What next.** Commit the arc, then 0121 through its own `/plan-impl`.
