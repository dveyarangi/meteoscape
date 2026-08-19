# 0034 · 2026-08-19 · Config lands by subtraction, and the corpus goes faceless

**Scope:** one ticket start to finish — 0123 through `/recall`, `/align`, five `/plan-impl` passes,
implementation, two `/review-impl` passes, `/sync-arch`, and the close — plus an unplanned privacy
scrub of the whole corpus and its git history. The session's shape was unusual: nearly every
implementation step ended in a *deletion*.

## Work done

- **`/recall` → the 0122→0129 renumber committed**, resolving 0033's fork: TWC's metric units
  falsified the unit-catalogue trigger, so the ticket moved behind its first plausible customer.
- **`/align` on 0123** — profile enumeration became declared data at composition roots (no global
  default, only profiles); `OfferingDef.secret_ref` deleted; the env spelling settled as one
  namespace per impl; the shipped catalogues left the root for `nodes/*/builtin.py`.
- **A privacy scrub, mid-session** — the deployment's identity and its domain vocabulary left the
  corpus, then its git history via `git filter-repo` and a force-push (both branches, verified
  zero hits across all rewritten history).
- **Five planning passes, then implementation**, then two review passes and a `/sync-arch`.
  Final state: 422 deterministic tests, ruff/format/pyright clean, all doc gates green.
- **The close** — six criteria checked, ticket and RFC moved into `done/` in one `move_doc`
  invocation, delivery status re-cut.

Footprint: **~240 lines** in `src` at close, against ~600 lines added and removed during the
session — most of the work was finding what should not exist.

## Settled this session

- **A def selects and ranks; it never restates what a manifest declares** — the calculator I/O
  group moved to `CalculatorManifest`, mirroring `OfferingSpec` as the provider's product row →
  [architecture § Config, binders, Weaver](../architecture.md#config-binders-weaver),
  [ADR-0005](../adr/0005-build-time-composition.md).
- **Availability is a system prop, enablement is an edge prop** — the shipped sets live in
  `nodes/providers/builtin.py` / `nodes/calculators/builtin.py`, the root declares only its
  profile; partially discharges [#26](../concerns.md#26-provider--calculator-plugin-scaffolding).
- **The catalogue handle *is* the id** — a plain string, so profiles select without retyping
  names and defs need no coercion machinery → same architecture bullet.
- **Key-absent refuses; there is no boot-degrade** — the public profile declares no keyed
  provider, so keyless runs are ordinary rather than degraded →
  [0123 (done)](../tickets/done/01-0123-config-secrets-degrade.md).
- **Env carries secrets and typed scalars, nothing structured** — per-offering `settings` are
  declared on the def; a config file may fill the same field later. Secrets are read *only* at
  names the declared `SecretSlot`s derive (empty ⇒ absent, environ wins over `.env`) →
  [architecture § Config, binders, Weaver](../architecture.md#config-binders-weaver).
- **`compose` takes an `impl_id`-keyed secrets map** — an embedder fills it from a vault with no
  env spelling at all → [edge/embedding.md](../edge/embedding.md) de-facto section.
- **A vendor-primary profile is deployment configuration, never the shipped root's shape** — and
  the deployment that wants one is the embedding edge's first client →
  [edge/embedding.md](../edge/embedding.md) Roadmap, [pilot requirements](../pilot-requirements.md).
- **`priority` defaults to 0, safely** — because the `priority` reconciler already resolves ties
  by bind order (stable sort) → [ADR-0004](../adr/0004-producer-resolution-and-capability.md).

## Built, then removed — the session's real subject

Five mechanisms were implemented and cut before close, each for a stated reason. Recorded because
the *pattern* outlives any one of them:

1. `OfferingDef.optional` (boot-degrade) — its only customer was a deployment-specific profile
   that does not belong in the public shape.
2. Config `Protocol`s + coercion helpers — ceremony; the short spelling came from id constants
   instead.
3. A weave-time tie refusal — it turned a *documented* behaviour (bind-order tie-break) into a
   boot error, contradicting the contract it claimed to protect.
4. The env `settings`-override channel — a config-file parser growing inside the env namespace,
   with no customer.
5. The unconsumed-var namespace sweep — residue of (4); it existed to feed the scanner.

Each was caught by a user challenge, not by a test or a gate. The common tell: a mechanism that
resisted naming (`DeploymentInputs`, `extras`, `substrate`, `provisions`) turned out to be a thing
that should not exist. **A name that will not settle is evidence about the design, not the word.**

## Found, not settled

- **`move_doc` misses a link whose markdown text spans a line break.** The close's inbound rewrite
  left one reference in
  [0125](../tickets/01-0125-supported-python-embedding.md) dangling; the integrity gate caught it
  immediately, and the fix was manual. The mover's contract says "nothing link-shaped to hand-edit"
  — multi-line link text is the exception, and it will recur at every close until the pattern is
  line-agnostic.
- **Deferring a decision *to* a ticket does not oblige that ticket to build a mechanism.** 0120's
  RFC deferred the cadence-override channel here; honouring the deferral literally produced (4)
  above. The obligation was to *decide* where overrides live, and the answer was "the field that
  already existed".

## Open questions

All live in their owning documents; cited, not restated.

- Storeless producers and self-homogenization, widened this session to any storeless producer →
  [#37](../concerns.md#37-storeless-materialized-producers-and-read-back-homogenization).
- Plugin discovery, optional sets, symmetric set selection →
  [#26](../concerns.md#26-provider--calculator-plugin-scaffolding).
- Whether the pilot's composition root is a parallel in-tree setup or a separate project →
  [0125](../tickets/01-0125-supported-python-embedding.md)'s align.
- Calculator satisfiability vs optional providers, now with no boot-time customer →
  [#35](../concerns.md#35-calculator-satisfiability-vs-optional-provider-degrade).

## Continuation

1. **0124 (vendor-call ledger)** is next in the queue — its own align precedes, and it rides the
   injection path 0123 just settled. The bee-line runs on the Open-Meteo path until the correction
   workstream, so nothing before it needs a live keyed provider.
2. **Sweep sessions 0028–0031 into `history/2026-08/`** once they age past the rolling window.
3. **`uv sync` stayed blocked** all session (the running MCP server holds `meteoscape.exe`); work
   ran under `--no-sync`. Environment fact, carried from 0032–0033.

## Advisory read

**What is great.** The corpus caught its own drift four separate times: the docs gate caught a
stale ticket path at close, `/review-impl` caught a `CompositionError` docstring advertising a
failure mode the ticket had made unrepresentable, `/sync-arch` caught two operator-visible rules
whose only homes were about to move into `done/`, and the validator sweep proved every named
edge-record test still exists. None of that depended on anyone remembering.

**What is good enough.** Five planning passes produced a plan that implementation then re-cut
twice more. The passes were not wasted — each found something real — but they validated a shape
that later review dissolved, which means the passes were probing *correctness of the plan* while
the open question was *whether the mechanism should exist*. Adversarial validation does not ask
that question; only a reader asking "what is this for?" does.

**What is questionable.** Four of the five removals were prompted by the user, not by the planning
or review skills. The skills are tuned to verify what is proposed, not to challenge whether it is
warranted — `/impact` asks "can it be narrower?", but only when invoked on a change already
believed necessary.

**What is out of balance.** The doc-to-code ratio inverted hard: roughly 600 lines of RFC and
ticket prose for ~240 lines of `src`, with the RFC amended seven times. A plan amended that often
during implementation is arguably being *written* during implementation.

**Hidden edges.** The `.env` decision was never made — it was inherited. Structured configuration
was pushed through an env namespace because env was what existed, and the cost (prefix grammar,
JSON parsing, collision guards) accumulated as *implementation detail* rather than surfacing as a
design question. The scrub of the deployment's identity had the same shape: the name entered the
corpus incidentally, one commit at a time, and only became visible when someone asked whether the
repo was public.

**What would make life easier.** A cheap "does this need to exist?" pass, distinct from
validation, run once before implementation rather than five times during it. The evidence it would
look for is already known: a mechanism with no named customer, a name that will not settle, a
guard that duplicates a documented contract.

**What next.** 0124's align.
