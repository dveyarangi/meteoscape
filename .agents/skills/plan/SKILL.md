---
name: plan
description: >-
  Use to plan or repeatedly validate a ticket's implementation RFC against
  its governing docs and code before implementation. Use when a ticket
  needs an RFC, or an existing RFC needs another validation pass.
---

Mechanism: not yet

- Explore documentation in depth, follow links in it to find all decisions
  relevant to current task. Find out which documented boundaries are involved,
  and whether implementation challenges them.

- If the ticket at hand is too coarse to yield a single unambiguous RFC, stop
  planning and decompose it into sub-tickets via
  [/ticket](../ticket/SKILL.md) first; then plan the first child.

- An RFC implements a ticket — no ticketless RFCs. If the task at hand has no
  ticket, create it first per `/ticket`; its behavior-altitude rule governs
  the criteria (shape stays in the RFC).

- When incepting, ask yourself - what is the cheapest real example that could
  prove this design assumption wrong?

- Run [/impact](../impact/SKILL.md) on the planned change. Record its output on
  the RFC.

- Establish implementation scope, pinpoint and mention affected boundaries,
  contracts, ownership. Present main code shapes - especially ones that
  represent documented boundaries. Present code flows.

- Detect implementation challenges and use [/align](../align/SKILL.md) to
  resolve them with the user.

- Do not select implementation shapes just because "that how it is usually
  done" or based on first idea. Promote simplicity, look for elegant solutions,
  prefer removing over expanding, prefer conciseness over verbosity.

- A hidden edge the plan names — a race, a migration step, a special case — that a
  choice of name, place or form brings with it reopens that choice before anything
  is built around it.

- Do not invent impl nouns or verbs that are not discussed or approved by
  user. Use existing vocabulary.

- If you see a concern, first check deeper how the existing architecture
  documentation describes it - it most probably already does. Read
  architecture.md, ADRs and the question store for this.

- Major goal of this planning is to find inconsistencies in the pre-planned
  architecture. Do this diligently. If such inconsistency found, do not stick
  blindly for architectural decision - instead raise concern with user to
  resolve it - either in code or in arch docs.

- Make the RFC determinate where a choice shapes observable behavior, a
  boundary or interface, ownership, failure semantics, compatibility,
  migration, or another non-local constraint. State the shaping fact with a
  reference to its durable owner; never rely on session context. Leave
  reversible implementation-local choices to `/tdd` and `/implement` unless
  they become load-bearing.

- The RFC (original or amended) must not describe load-bearing architecture
  absent from the architecture docs — land the decision in the docs first
  (`/align` when needed), then reference it from the RFC. What fails the entry
  file's load-bearing counter-test belongs in code and its comments, however
  closely an architecture sentence already describes it. Write each sentence
  landed there as its invariant and its pointer: the reasons stay with the
  decision that holds them, and what a mechanism or a script owns stays there.

- Describe the implementation stages; allocate them according to `/tdd`
  rules. Look at stages to make sure each of them keeps the tests green; in
  case that would take too much temporary effort, allow red, note about test
  status and compact reason for it.

- Map out scope-specific limitations, follow-ups and related out-of-scope
  concerns.

- Prefer reuse and reduction of existing nouns, verbs and adjectives; when
  adding shape - make sure documentation supports it, if in any doubt - `/align`
  with user.

- Any wrinkle against architecture should be resolved; when solution is not
  found or following first-principles makes the code weird - align with user.
  Architecture must lead code shape even if code disagrees. Do not expose
  public methods or create flows that are not in architecture.

- If planned code includes a temporary solution that is dissolved by future
  development, add RFC instruction to append TODO comment to code that flags
  this. Otherwise code changes can start relying or considering the temporal
  code, which can be hard to disentangle later.

- Repeated invocations are validation passes over the same RFC. Re-read
  the ticket, RFC, durable docs, and relevant code; challenge the plan against
  new evidence and amend it in place. Do not create a replacement RFC merely
  because the plan changed before implementation.

- As an additional pass, try to explain things to yourself simply, as if you
  are teaching the architecture, and being asked reasonable question and look
  for areas that evade simple or common-sense explanation.

- Validate the RFC adversarially on every pass:
  - Probe each boundary and stage with counterexamples, including empty, partial,
    faulting, and raced outcomes where relevant.
  - Make every planned test prove the intended behavior and failure reason, not
    merely that the path succeeds or raises.
  - Separate sourced facts and existing invariants from assumptions; verify
    facts in code or authoritative sources and surface load-bearing assumptions
    for `/align`.
  - Reject pseudocode or prescribed structure that introduces undocumented
    architecture or freezes a reversible local choice.
  - Check that every new promise names how it will be validated, and that
    the stages collectively prove the ticket's acceptance criteria.

- Repeat validation using this skill until no load-bearing ambiguity,
  contradiction, or unverified assumption remains. The RFC may permit multiple
  equivalent local implementations when they preserve the same documented shape
  and proof.

- If repeated validation keep bringing up gaps, take a step back and look
  at what causes this oscillation. The architecture, ADRs, tickets are not
  carved in stone, they can have real contradictions or inconsistencies that cause
  it. Look into the core reasons and `/align` on them again if needed.

- Overall, always consider future development and potential code reuse when
  selecting code shapes.

- Cover migrations, compatibility, rollout, failure handling, and observability
  when relevant.

- Record the plan as an RFC; its name and home are installed below.

- RFC header: H1 is the ticket's title plus ` — implementation plan`; then
  `- **record of** what it intends to become`, which the mover turns to
  `what happened` at close; then `**Authored:** YYYY-MM-DD`, and `**Last amended:** YYYY-MM-DD` once a later
  pass changes the plan; then one line stating what it implements, linking the
  ticket.

- DO NOT CHANGE THE CODE!

## Installed from other mechanisms

<installed by="ticket">
**P6** Name the RFC by the owning ticket's basename, under `docs/rfc/`, with no serial of its own; it
moves to `docs/rfc/done/` with the ticket.
</installed>
