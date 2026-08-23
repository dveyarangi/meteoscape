# 0037 · 2026-08-24 · The corpus learns to merge, and false sharing is cut

**Scope:** the first skill-corpus merge — the peer project's skill tree read end to end, its
merging-and-separation procedure ported and extended, and `docs/process.md` incepted, twice: first
by relocating to-tickets' machinery, then re-cut to only what is genuinely shared after the user
asked *who actually reads this?* Between sessions, 0124.0020's plan work landed dated resolutions
in its tickets from outside this repo's chats; that arc continues and is not concluded here.

## Work done

- **The divergence read**: full `diff -qr` of the two corpora. The peer's governing idea —
  bodies project-free, local facts behind appendices and `<project-local>` blocks, merge = port
  bodies only — ported into skill-up. Their process.md, initiatives machinery, and guard-script
  rewrites recognized as their project-local half and left; their guard scripts turned out to be
  *meteoscape's own machinery* adapted, so nothing flowed back.
- **Nine skills touched**: to-tickets de-projected (and its `Blocked by`/`Depends on`
  inconsistency closed), commit's gate set moved behind a `<project-local>` block, recall given
  local pointers, edge/to-spec repointed, align's tree diagram and sync-arch's `adr/` path fixed,
  the README taught the Windows symlink-clone recovery for `.cursor/skills` and `.claude/skills`.
- **process.md incepted, over-cut, and re-cut.** The first cut mirrored the peer's split and
  moved the RR-NNNN scheme and Status vocabulary out of TICKET-FORMAT; the user challenged the
  sharing claim, and the reader-count agreed — only `/to-tickets` allocates positions. The
  machinery went back; process.md kept the in-repo seam, the cross-document naming, and the skill
  loop in text.
- **Deliberately not merged**: initiatives (trigger — several requests meaningful only together —
  absent here), the peer's Notion-based process content, merge tooling and core-override semantics
  (one merge is one shape).

## Settled this session

- **Skill bodies stay free of project facts**; what is local lives in an appendix or a
  `<project-local>` block, and a block *adds, never overrides* →
  [skill-up § Project-local divergence](../../.agents/skills/skill-up/SKILL.md).
- **Merging is manual and body-only**: port body changes fixing defects as you go; appendices and
  local blocks stand; a skill in only one corpus is local by intent or not yet ported — ask →
  [skill-up § Merging a reference corpus](../../.agents/skills/skill-up/SKILL.md).
- **`docs/process.md` is a corpus convention** — citable from bodies like `glossary.md`, contents
  project-owned, built lazily as the process incepts or changes → same section.
- **Meteoscape's process.md holds only connective tissue** — the in-repo seam, the naming that
  links spec/ticket/RFC, the skill loop → [process.md](../process.md).
- **Ticket machinery is to-tickets-local, not shared** — the RR-NNNN scheme and Status vocabulary
  returned to [TICKET-FORMAT.md](../../.agents/skills/to-tickets/TICKET-FORMAT.md) after the
  relocation failed the *who reads this?* test.

## Found, not settled

- **A split can be ported for its shape rather than its reason.** The peer's naming section is
  genuinely cross-doc (one dated-slug scheme over every doc type); meteoscape's RR-NNNN is
  ticket-only. Mirroring the cut without checking why it sat where it did produced a page of false
  sharing that survived until the user asked who the readers were — the same *who reads this?*
  probe that dissolved `Site` in 0036, now catching a document instead of a type.
- **The separation rule is aspirational even at its origin** — the peer's own edge body names
  their process.md's seam section; enforcement everywhere is by eye. Nothing checks a SKILL.md body
  for project facts, so purity drift will be silent until the next merge trips over it.
- **The peers now disagree about the procedure itself.** Meteoscape's skill-up carries the fixed
  and extended merge rules; the peer still has the first draft. Until a merge runs the other way,
  each corpus follows a different authority for the same act.

## Open questions

None became durable product pressure — `concerns.md` gained nothing from this session. Two
watch-items whose owner is the next merge event itself:

- Whether merging deserves tooling (strip appendices and blocks, diff bodies) — deferred until a
  second merge shows the real shape; the procedure's text stays the only mechanism.
- Whether initiatives ever earn a port — the trigger is several requests that only mean anything
  read together; the peer's `INITIATIVE-FORMAT.md` (in its own repository) is the known pull
  location if the pilot's downstream ever splits into such pieces.

## Continuation

1. **0124.0020** — plan resolutions dated 2026-08-22 sit uncommitted in its ticket, its sibling,
   and `concerns.md` (#48's widened convention gap); that arc commits with its own work, not with
   this session's. Implementation is next.
2. **Back-port at the next merge with the peer corpus**: the skill-up extensions (defect-fixing clause,
   no-override rule, single-corpus clause, process.md-as-convention) exist only on this side.

## Advisory read

**What is great.** The re-cut. The corpus's own probe — *who reads this?* — was turned on the
merge itself by the user, and the answer reversed a page of freshly enacted work within one
exchange. The procedure that made this cheap is now written down in skill-up, so the next merge
starts from rules rather than archaeology.

**What is good enough.** Manual merging. One merge in the corpus's life is no basis for tooling,
and `diff -qr` plus judgment covered twenty-one skills in one session.

**What is questionable.** Edge's body line — "`process.md` owns delivery state" — is now true only
transitively (process.md hands the reader on to the queue). Kept for body parity with the peer, but
it is the kind of one-hop honesty that a future reader may trip on.

**What is missing.** A purity gate. The docs guards check links and queue agreement; nothing checks
that a SKILL.md body is project-fact-free — the exact drift this merge existed to repair, and the
first thing that will silently regrow.

**Hidden edges.** The `<project-local>` blocks are prose conventions with no parser: nothing warns
when a block contradicts its body, which is the one thing the no-override rule forbids.

**What next.** 0124.0020's implementation; the back-port when the peer corpus next merges.
