# Edge record format

One record per edge, a living document at `docs/edge/<edge>.md`, named by the edge — `hosts.md`,
`installation.md`, `mcp.md`. No numbers, no `done/`: the record never completes, and its history
is git's. An edge things attach to keeps one sidecar per extension at
`docs/edge/<edge>/<extension>.md`.

An **edge** is where the system meets those who consume it or extend it. Its record holds what the
system promises them, what it requires of what attaches to it, the checks a new attachment passes,
where each attached thing stands, the edge's open questions, and its staged evolution. The
audience is the project at work, user and agents. Text written for a consumer or an extender — a
tool description, a public API doc, the front page, an install guide — is **derived from** the
record and stays a subset of it.

The record informs. Nothing an integration needs to work is read from it: the integration is code
and configuration in its own home, and the record names it.

## The record

```md
# Edge — {Name}

- **Status:** Stub | Normative | Normative (tentative)

## Contract

## Invariants

## Extending

## Extensions

## Concerns

## Roadmap
```

Sections appear in this order and no others. `Extending` and `Extensions` appear together, on an
edge things attach to, or neither does.

- **Contract** — the edge as built: what it promises those who consume it, and what it requires of
  what attaches to it. Reference canonical semantics (ADRs, architecture) instead of restating
  them.
- **Invariants** — the strict behaviour owed at the edge, one bullet each, each naming its
  validator inline: `*validated by:*` and a backticked path to the test that asserts it, or
  `*validated by:* live —` and the `Extending` check that observes it. A promise with no validator
  is marked **⚠ unguarded**.
- **Extending** — the checks a new extension passes, in general terms: a numbered list, one check
  each, `1. **<check>** — <what it observes>`. The same checks hold for every extension, and are
  passed again when one changes upstream.
- **Extensions** — one row per extension attached:

  ```md
  | extension | standing | sidecar |
  |---|---|---|
  | Claude Code | every check observed but two | [claude-code](hosts/claude-code.md) |
  ```

  `standing` is a few words; the sidecar holds the evidence. Every file in `docs/edge/<edge>/` is
  a row's sidecar.
- **Concerns** — edge-scoped open questions and risks: pointers into the question store,
  `docs/questions/`, which stays their owner, each with its edge-local reading.
- **Roadmap** — the staged evolution of the edge, one line per stage, linked to its owning ticket.
  Plans, not promises.

## The sidecar

```md
# {Extension} — {Name} edge

## Integration

## Conformance
```

- **Integration** — where the extension's integration lives, every part backticked: files,
  configuration, the code written for it, and what it needs from outside the tree — an approval,
  a version, a setting. Where to look, never a copy of what is there.
- **Conformance** — one bullet per check of the record's `Extending`, named as it names it,
  `- **<check>** — <result>`, the result opening with one of: `observed <date>`, with the version
  where known and what was seen; `documented`, with the source; `unobserved`; `absent`, with what
  stands in.

## Rules

- **Normative core, descriptive periphery.** `Contract` and `Invariants` are promises: in a
  `Status: Normative` record everything there is true of the live edge, and `Stub` is the only
  license for aspiration. **`Normative (tentative)`** is the state between: the record is
  load-bearing for what it states, but a landing ticket is reshaping the edge, so a promise may
  carry **⚠ pending — \<ticket\>**, naming the ticket and stage that clears it. It is not a softer
  `Normative`: an unmarked claim in a tentative record is held to the same standard, and the
  qualifier goes with the commit that lands the change. `Extensions`, `Concerns` and `Roadmap` are aggregation — pointers and plans,
  never validated, carrying no delivery-status vocabulary
  → [Status](../ticket/TICKET-FORMAT.md#status).
- **Per-invariant validators, not a separate section.** Each promise points at what enforces it,
  so a check can see the validator still exists. **⚠ unguarded** is legal in a Stub, a finding in
  a Normative or tentative record.
- **An observation is what was watched.** Nothing unwatched is written `observed`, and a partial
  watch says which part. An observation keeps its date; a later one replaces it.
- **Aggregate by reference.** The question store owns open questions, tickets own delivery state,
  the architecture owns the internal shape, the code owns the integration — the record holds the
  edge-local projection and the link, never a copy.
- **Derivations are subsets.** Any text for a consumer or an extender must be derivable from the
  record; if it says something the record does not, the record is behind — fix it first.
- **A contract change is named out loud.** An edit that changes a promise is declared breaking or
  compatible at the moment it is made. When a Roadmap entry's ticket lands, the same edit that
  updates `Contract` removes the entry.
- **The check.** `edges.py --check` holds the form it can read, never whether a promise is true:
  the title and status, the sections and their order, a validator or **⚠ unguarded** on every
  invariant and an unguarded one only in a Stub, a validator path that exists and a live validator
  naming a check, the checks' form, a sidecar for every row and a row for every sidecar, each
  sidecar's title and sections, and one result per check, each opening with its word and an
  observation with its date. Whether a Concern points into the store, a Roadmap line links a
  ticket, a `documented` result names its source or an `absent` one what stands in, is the
  reader's.
