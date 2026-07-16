---
name: denoise
description: >-
  Deduplicate and clean up prose docs and inline code comments — one canonical
  home per fact, → links elsewhere, trim settled evolution prose.
---

# Denoise

User-named paths only. Learn where this repo already treats each fact as
authoritative; follow that layering — do not invent one. Out of scope: code
structure, contradictory passages, reorganizing where facts live.

**Deduplicate.** A fact is explained once, at its canonical home; elsewhere
replace the restatement with `→ [<label>: <hint>](<path>#<anchor>)` — one
pointer, no re-teaching. Same-level repetition is noise; a higher-level summary
that points to deeper detail is not — keep it, along with minimal standalone
context and diagram labels. Normalize link style in files you touch.

**Doc evolution.** After a decision settles, state what is true now — not how
you got here. Remove superseded paths, unchosen alternatives, completed
migration notes. Keep a rejection only when it is load-bearing (structural
constraint or guardrail). Delete evolution prose; do not link it.

**Inline code docs.** Docstrings describe what *this unit* does — not pasted
domain definitions.

**Workflow.** Scan → inventory **Safe** / **Needs you** → apply safe items
(obvious dupes, non-load-bearing evolution, link normalization) → pause on
ambiguous homes, cross-layer moves, large deletions, or contradictions →
verify links → summarize.

**Completion**
Make sure fully resolved tickets and RFCs are moved to their corresponding /docs/../done folder.