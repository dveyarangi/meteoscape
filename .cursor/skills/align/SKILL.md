---
name: align
description: Grilling session that challenges your plan against the existing domain model, sharpens terminology, and updates documentation (glossary.md, ADRs) inline as decisions crystallise. Use when user wants to stress-test a plan against their project's language and documented decisions.
---

<what-to-do>

Interview me relentlessly about every aspect of this plan until we reach a shared understanding. Walk down each branch of the design tree, resolving dependencies between decisions one-by-one. For each question, provide your recommended answer.

Ask the questions one at a time, waiting for feedback on each question before continuing. Asking multiple questions at once is bewildering. Do not use platform (Cursor/Claude Code) question format, output plain md.

If a *fact* can be foundby exploring the codebase, look it up rather than asking me. The *decisions*, though, are mine - put each one to me and wait for my answer.


Do not enact the plan until I confirm we have reached a shared understanding.
</what-to-do>

<supporting-info>

## Domain awareness

During codebase exploration, also look for existing documentation:

### File structure

Most repos have a single context:

```
/
├── docs/
│   └── adr/
│       ├── 0001-event-sourced-orders.md
│       └── 0002-postgres-for-write-model.md
├────── architure.md
├────── product.md
├────── glossary.md
└── src/
```

If a `CONTEXT-MAP.md` exists at the root, the repo has multiple contexts. The map points to where each one lives:

```
/
├── CONTEXT-MAP.md
├── docs/
│   └── adr/                          ← system-wide decisions
├── src/
│   ├── ordering/
│   │   ├── glossary.md
│   │   └── docs/adr/                 ← context-specific decisions
│   └── billing/
│       ├── glossary.md
│       └── docs/adr/
```

Create files lazily — only when you have something to write. If no `glossary.md` exists, create one when the first term is resolved. If no `docs/adr/` exists, create it when the first ADR is needed.

## During the session

### Challenge against the glossary

When the user uses a term that conflicts with the existing language in `glossary.md`, call it out immediately. "Your glossary defines 'cancellation' as X, but you seem to mean Y — which is it?"

### Sharpen fuzzy language

When the user uses vague or overloaded terms, propose a precise canonical term. "You're saying 'account' — do you mean the Customer or the User? Those are different things."

### Discuss concrete scenarios

When domain relationships are being discussed, stress-test them with specific scenarios. Invent scenarios that probe edge cases and force the user to be precise about the boundaries between concepts.

### Cross-reference with code

When the user states how something works, check whether the code agrees. If you find a contradiction, surface it: "Your code cancels entire Orders, but you just said partial cancellation is possible — which is right?"

### Update glossary.md inline

When a term is resolved, update `glossary.md` right there. Don't batch these up — capture them as they happen. Use the format in [GLOSSARY-FORMAT.md](./GLOSSARY-FORMAT.md).

`glossary.md` should be totally devoid of implementation details. Do not treat `glossary.md` as a spec, a scratch pad, or a repository for implementation decisions. It is a glossary and nothing else.


## Update architecture.md inline

When high-level architecture of this project changes, update `architecture.md`. Use format in [ARCH-FORMAT.md](./ARCH-FORMAT.md).

`architecture.md` document captures the **high-level architecture**. Lower-level concerns are intentionally **deferred** and listed at the end.
> Scope note: everything here is at the architecture/contract level. Where a concrete shape would prematurely lock a deferred decision, we define only the *seam*.
> You should guide the user toward deep modules with simple boundaries.


### Extract open questions and risks

Open questions and risks should live in [docs/concerns.md](./docs/concerns.md) The concerns should be sorted highest priority first; Settled items move out to other architecture docs.

### Offer ADRs sparingly

Only offer to create an ADR when all three are true:

1. **Hard to reverse** — the cost of changing your mind later is meaningful
2. **Surprising without context** — a future reader will wonder "why did they do it this way?"
3. **The result of a real trade-off** — there were genuine alternatives and you picked one for specific reasons

If any of the three is missing, skip the ADR. Use the format in [ADR-FORMAT.md](./ADR-FORMAT.md).

</supporting-info>
