---
name: denoise
description: >-
  Deduplicate and clean up prose docs and inline code comments — one canonical
  home per fact, → links elsewhere, trim settled evolution prose.
---

# Denoise

The topic in context or entire codebase, on user request. Learn where this repo already treats each fact as
authoritative; follow that layering — do not invent one. Out of scope: code
structure, contradictory passages, reorganizing where facts live.
Always explore `architecture.md`, `glossary.md` and relevant ADRs too.

**Unwrinkle.** Cross-explore for contradictions, under or overstatements, redundancies or other misalignments between docs, make sure different architecture docs are aligned with each-other. 
In case of load-bearing or rippling contradiction, ask user about resolution, explaining the context and providing ways to amend with recommendation. Use `/align` skill if decision is multi-step.
Exclude previous sessions and RFC - they are historical records, not architectural statements. All truth statement should live in architecture, adrs or code.

**Deduplicate.** A fact is explained once, at its canonical home; elsewhere
replace the restatement with `→ [<label>: <hint>](<path>#<anchor>)` — one
pointer, no re-teaching. Same-level repetition is noise; a higher-level summary
that points to deeper detail is not — keep it, along with minimal standalone
context and diagram labels. Normalize link style in files you touch.

**Doc evolution.** After a decision settles, state what is true now — not how
you got here. Remove superseded paths, unchosen alternatives, completed
migration notes. Keep a rejection only when it is load-bearing (structural
constraint or guardrail). Delete evolution prose; do not link it.
Note that future development/planned extension prose can stay in docs/code where is relevant. But session/ticket references should not appear in code docstrings.

**Inline code docs.** Docstrings describe what *this unit* does — not pasted
domain definitions.

**Session, tickets and RFCs** are allowed to carry duplicate relevant architectural context; those docs are not core architecture, but historical records or current work digests. Their corresponding `README.md` files should be pure, though.
Core architecture docs must not reference sessions, tickets or RFCs.

**Workflow.** Scan → inventory **Safe** / **Needs you** → apply safe items
(obvious dupes, non-load-bearing evolution, link normalization) → pause on
ambiguous homes, cross-layer moves, large deletions, or contradictions →
verify links → summarize.

**Completion**
Make sure fully resolved tickets and RFCs are moved to their corresponding /docs/../done folder, references to them updated.