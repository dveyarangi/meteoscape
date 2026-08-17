# 0030 · 2026-08-17 · the Allowance lands before TWC

**Scope:** the second session of 2026-08-17. A `/recall`, a `/plan-impl` validation pass over 0120
that found the build it prescribes cannot boot, an `/align` that minted the Allowance, a new ticket
(0118) planned through four RFC passes, its implementation landed externally, two `/review-impl`
passes, and a `/sync-arch` that caught the missed-passage trap — twice.

## Work done

- **`/recall`** — 0119 delivered, tree green at 324, 0120 nominally Ready with the capture fixture
  as its first criterion.
- **A `/plan-impl` pass over 0120 found two real defects in the plan.** TWC's documented 1.5 m
  screen height against Open-Meteo's 2 m makes reach composition **incomparable on Z**, so the
  key-present boot the ticket's criteria demand raises `CompositionError` — verified by running the
  fold, not by reading it. And 0119's `cadence ≤ max_lead` guard (a `ValueError`) escapes `build`
  unwrapped, refusing **two** of the seven offering rows at the default cadence, not one.
- **`/align`, three items** — the Allowance decision (below); the guard's documented justification
  measured false and rewritten; all seven offerings kept with a teaching boot error.
- **0118 minted, planned, and validated through four RFC passes.** Pass 2 found the band-as-written
  breaking ADR-0007's tie law; pass 3 found the RFC's own boundaries table stating the pre-fix rule,
  plus the serialization-surface and witness-transitivity facts, both checked by simulation over
  real footprints; pass 4 found one rename leftover and the cellular-blind robustness fact. The
  field was renamed `z_allowance` on the user's catch that the identifier should match the seam.
- **The numbering scheme's insertion example was itself the bug.** The first mint took `01195`,
  which reads as 1195; renumbered to the free slot `0118`, and TICKET-FORMAT's `00105` example —
  the same defect in the rule's own illustration — was fixed to a four-digit rule.
- **0118 implemented externally, then two `/review-impl` passes** — a close match with better tests
  than planned; three findings applied (the as-landed signature note, the RFC's `done/` move with
  link re-depth, one over-pinned tie assertion loosened).
- **`/sync-arch`** — two live passages still stating the pre-0118 world, both fixed.
- **RFC 0120 amended in place**: the 0118 dependency, `build`'s `CompositionError` wrap with the
  short-offering refusal tests, the MCP-edge boundary row corrected from "Unchanged" to compatible
  addition, and eight drifted line citations repaired.

Footprint: **263 insertions / 29 deletions** across `src` and `tests` (+11 tests, 335 green,
pyright clean) against **~170/-50** in docs — the second code-forward stretch in a row.

## Settled this session

- **Sample levels compose by Allowance, not containment** — the Parameter declares the band of
  interchangeable levels; fallback is accepted quality degradation, accepted by declaring its
  bound → [ADR-0007](../adr/0007-capability-carries-its-domain.md).
- **The Allowance is a licence, never a constraint** — equal levels compose as a tie regardless;
  the band only extends composability → [ADR-0007](../adr/0007-capability-carries-its-domain.md),
  [parameters.md](../parameters.md#sample-level-allowance), [glossary](../glossary.md).
- **`z_allowance` is an id-entailed optional `ParameterDef` fact**, plain floats so the parameters
  leaf stays manifold-free → [ADR-0002](../adr/0002-data-model.md).
- **The v1 bands**: WMO screen `[1.25, 2.0] m` for temperature and humidity; exact elsewhere →
  [parameters.md](../parameters.md#sample-level-allowance).
- **`cadence ≤ max_lead`'s real justification is spend governance and `exp` honesty**, not
  unservability — the fall-behind story died with 0119's retention predicate; measured at 5
  calls/day against a configured 2 → [ADR-0003](../adr/0003-provenance-and-origin.md),
  [edge/provider.md](../edge/provider.md).
- **All seven TWC offerings stay declared; an under-long duration at the configured cadence is an
  incoherent pairing refused at boot** by a `CompositionError` naming both numbers and the knob →
  [0120's acceptance criterion](../tickets/01-0120-twc-provider.md).
- **`compose_domains` takes the `ParameterDef`, replacing the `ParameterId`** — landed shape,
  recorded as a decision → [RFC 0118 closing note](../rfc/done/01-0118-sample-level-allowance.md);
  reverses a choice recorded in done ticket 0060, which stays as written.
- **Ticket positions stay four digits**; an exhausted gap takes the nearest free slot on the
  correct side, noted in the queue row → TICKET-FORMAT (skill-owned).
- **0118 delivered** → [delivery status](../tickets/README.md); 0120 is Ready again.

## Found, not settled — new pressure

- **Concern #46 grew.** The incomparability path is now *reachable* (out-of-band refusal), and the
  band sentence is more prose authored inside geometry — recorded there; the diagnostic's shape
  still waits on the real regional configuration →
  [#46](../concerns.md#46-composition-failure-attribution-is-paid-inside-geometry).
- **Cross-parameter band licensing at the calculator fold** is deliberately untouched; the question
  (whose band licenses a cross-level input comparison) is parked in the
  [RFC's limitations](../rfc/done/01-0118-sample-level-allowance.md) beside
  [#38](../concerns.md#38-calculator-admittance-is-fixed-pointwise-total).

## Continuation

1. **0120 (TWC as primary)** — genuinely Ready now; the capture fixture out of `tmp/twc_capture/`
   is its first acceptance criterion and still sits on one machine.
2. **The CI link + encoding check** — fourth session running, still unticketed →
   [cicd.md](../cicd.md#ci-pipeline).
3. **Sweep session 0026 into `history/2026-08/`** — carried from 0029, still pending.

## Advisory read

**What is great.** The validation pass earned its keep before a line of code existed: the Z
incomparability was found by *running the fold against the planned declarations*, not by reading
docs — and it was an architecture gap, not a plan typo. The premise that broke (a sample level is
an extent) had survived every document because no second screen height had ever been declared.

**What is good enough.** The four RFC passes showed clean convergence — a rule defect, then an
internal inconsistency, then a leftover word — and the implementation followed the plan closely
enough that both reviews found only improvements to record, not drift to repair.

**What is questionable.** Pass 2's tie-law fix was itself incomplete: it amended the rule table but
not the boundaries row three paragraphs up, and pass 3 had to catch it. The same class of failure
then reappeared at sync-arch scale — ADR-0007's own X/Y bullet still said "containment only" after
the align amended the bullet beside it. An amendment is not self-reviewing; this session now has
three instances across two artifacts.

**What is missing.** Still a running TWC leaf. The gap is again exactly one ticket wide, and this
time nothing in front of it is undecided.

**What is out of balance.** The user's two catches — the five-digit position and the field name —
were both *naming* defects that every validation pass had walked past while probing semantics. The
passes verify what code will do; what things are called still has no instrument but a reader.

**Hidden edges.** The numbering bug was in the format's own example: the rule taught the defect.
When a convention document illustrates by example, the example is load-bearing and can be wrong
independently of the rule's intent — nothing checked it, because it looked like documentation.

**What would make life easier.** The CI check, for the fourth session running — link resolution
would have caught the RFC move's missed `../edge/` family mechanically instead of by a hand-rolled
loop that itself misfired once on a working-directory surprise.

**What next.** 0120, starting with the fixture.
