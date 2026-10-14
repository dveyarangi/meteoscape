---
name: align
description: Grilling session that challenges current plan against the existing domain model, sharpens terminology, and updates documentation as decisions crystallise. Use to stress-test a plan against their project's language and documented decisions.
---

Mechanism: not yet

<what-to-do>

Begin every alignment with a **necessity gate**: name the present customer, the observable problem, and why existing behaviour cannot satisfy it. An accepted requirement or ADR passes by citation. Weak evidence means narrow, postpone, or eliminate — settle that before exploring design. The gate fires late too: a mechanism whose name will not settle is evidence it should not exist. [/impact](../impact/SKILL.md) traces consequences once the need holds.

Problem before machinery: open with the concrete failures and my own earlier words, read back from the records, before any design question. A new term is a decision, not a convenience; when I do not follow, go more concrete.

Interview me relentlessly about every aspect of current work until we reach a shared understanding. Walk down each branch of the design tree, resolving dependencies between decisions one-by-one. For each question, provide your recommended answer. If there are alternatives, show pros/cons/tradeoffs between them.

Ask the questions one at a time, waiting for feedback on each question before continuing. Asking multiple questions at once is bewildering. Do not use platform (Cursor/Claude Code) question format, output plain md.

If a *fact* can be found by exploring the doc corpus or codebase, look it up rather than asking me. The *decisions*, though, are mine - put each one to me and wait for my answer.

Decomposing the work during an align is [/ticket](../ticket/SKILL.md)'s, and it calls
[/impact](../impact/SKILL.md) on the draft split. Run that chain and present what it returns as a
suggestion; do not mint. A breakdown reached by unaided grouping is not that chain's output,
however ticket-shaped it looks.

Do not enact the plan before I confirm we have reached a shared understanding.


</what-to-do>

<supporting-info>

## Good architecture

Goal of architecture is to reduce work on creation and maintenance of the system.

Identify the load-bearing assumption behind the proposed shape; ask yourself - what is the cheapest real example that could prove this design assumption wrong? 

Check it when practical, preferably against external reality rather than our own documents and tests.

If falsified, realign.
If unverified and load-bearing, preserve the uncertainty explicitly.

## Domain awareness

During codebase exploration, also look for existing documentation:

### File structure

Most repos have a single context:

```
/
├── docs/
│   ├── adr/
│   │   ├── 0001-event-sourced-orders.md
│   │   └── 0002-postgres-for-write-model.md
│   ├── architecture.md
│   └── glossary.md
└── src/
```

Create files lazily — only when you have something to write. If no `docs/glossary.md` exists, create one when the first term is resolved. If no `docs/adr/` exists, create it when the first ADR is needed.

## During the session

### Challenge against the glossary

When the user uses a term that conflicts with the existing language in `docs/glossary.md`, call it out immediately. "Your glossary defines 'cancellation' as X, but you seem to mean Y — which is it?"

This cuts both ways: before *you* propose a name, check the glossary yourself — including its _Avoid_ lists, which are reservations, not suggestions. If every synonym for a concept is avoided, that is a designed constraint telling you which word the project has chosen; work within it rather than proposing around it.

### Check whether it was already decided

Before treating a question as open, search the ADRs and architecture docs for it. A surprising amount of "open" questions are accepted decisions the code drifted from — the answer then is "implement the ADR", not a fresh trade-off analysis. Cite the deciding document when you find one.

### Challenge against the Edge records

<installed by="edge">
**E3** When the plan touches an edge — where the system meets those who consume it or extend it — check
that edge's record under `docs/edge/`. A contradiction with its Contract or Invariants is either a
plan bug or a deliberate contract change, and a contract change is named **breaking or
compatible** out loud before proceeding. As decisions land, write them into the record in the
shape of `.agents/skills/edge/EDGE-FORMAT.md`: a contract change in `Contract` and `Invariants`,
marked `⚠ pending — <ticket>` until its ticket lands and the record set `Normative (tentative)`
while any is pending, a promise without a validator marked **⚠ unguarded**; newly surfaced
edge-scoped concerns as pointers in `Concerns`; staging shifts in `Roadmap`.
</installed>

### Lead with the decisive fact

When recommending between alternatives, find the fact that settles it — a reader count, an import direction, an existing invariant, what a test actually asserts — and lead with it. A pros/cons menu with no decisive fact means you haven't explored enough yet; go look before asking.

### Name the shared assumption

When posing an A-or-B fork, state the assumption both branches share. The user's best answer may dissolve the fork rather than pick a branch — treat "the premise is wrong" as a first-class outcome, not a detour. If a fork keeps resisting resolution, that is usually the sign.

### Sharpen fuzzy language

When the user uses vague or overloaded terms, propose a precise canonical term. "You're saying 'account' — do you mean the Customer or the User? Those are different things."

### Discuss concrete scenarios

When domain relationships are being discussed, stress-test them with specific scenarios. Invent scenarios that probe edge cases and force the user to be precise about the boundaries between concepts.

### Cross-reference with code

When the user states how something works, check whether the code agrees. If you find a contradiction, surface it: "Your code cancels entire Orders, but you just said partial cancellation is possible — which is right?"

### Update glossary.md inline

When a term is resolved, update `docs/glossary.md` right there. Don't batch these up — capture them as they happen. Use the format in [GLOSSARY-FORMAT.md](./GLOSSARY-FORMAT.md).

`docs/glossary.md` should be totally devoid of implementation details. Do not treat it as a spec, a scratch pad, or a repository for implementation decisions. It is a glossary and nothing else.

### Update architecture.md inline

When high-level architecture of this project changes, update `architecture.md`. Use format in [ARCH-FORMAT.md](./ARCH-FORMAT.md).

`architecture.md` document captures the **high-level architecture**. Lower-level concerns are intentionally **deferred** and listed at the end.
> Scope note: everything here is at the architecture/contract level. Where a concrete shape would prematurely lock a deferred decision, we define only the *seam*.
> You should guide the user toward deep modules with simple boundaries.


### Land resolutions as they are made

Land each resolution the moment it is made, as the blocks below say.

<installed by="mechanism-shape">
**R5** Land a mechanism's rule in AGENTS.md only as an installed block from its rules file. While the
mechanism is undeclared, write the rule by hand and wrap it as a straw dog bound to the question
of what the mechanism owns, as you write it.
</installed>

<installed by="ticket">
**P7** Rewrite the ticket in place to what the align's landed decisions make true.

**P10** Open an align by saying what its work is: what it builds and the problem it answers, in plain
words, each of its terms explained, before the necessity gate or any question.

**P11** Sweep the question's body, and the ticket where there is one, for internal consistency at the end:
an early line may still assert what a later resolution changed.
</installed>

<installed by="questions">
**Q6** Land a decision as it is made, with its provenance: final in its durable home where no open
question's answer can change its form or home, otherwise as a straw dog bound to the nearest open
ancestor whose answer can. One with nowhere to land yet — its home is work not done — is a line in
the `## Decisions` list of the lowest question holding everyone who needs it, and takes
`→ <link>` when it lands. Close the question it answers against where it landed, and when a line
lands, repoint every entry closed against its list there.
</installed>

<installed by="product">
**U2** When a question under *What is this project for?* is decided with something to build, do three
things in one step:

1. With `/product`, write the answer into the document: a row that waits on this question has
   its *waits on* cell emptied; otherwise a new row takes the next number.
2. Close the question against that row.
3. Open the question of how to build it in the *How is this project built?* branch, under the
   question it belongs to, and give it its trace link with `questions.py realize`, naming the
   row's number and name.

A decision that changes, replaces or retires an answer is written by `/product` the same way.
</installed>

### Offer ADRs sparingly

Only offer to create an ADR when all three are true:

1. **Hard to reverse** — the cost of changing your mind later is meaningful
2. **Surprising without context** — a future reader will wonder "why did they do it this way?"
3. **The result of a real trade-off** — there were genuine alternatives and you picked one for specific reasons

If any of the three is missing, skip the ADR. Use the format in [ADR-FORMAT.md](./ADR-FORMAT.md).

</supporting-info>
