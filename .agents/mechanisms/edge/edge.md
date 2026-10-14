# edge — holds what the system promises those who consume it and requires of those who extend it, one record per edge

- **instruction** `.agents/skills/edge/SKILL.md` — the act: establishing a record, attaching an extension and passing its checks, monitoring, validating, deriving
- **state** installed
- **record of** what must always hold

## How it works

An **edge** is where the system meets someone outside it: a consumer of what it promises, or an
extender attaching to it — a host and its integration, a recipient project with its own
mechanisms. Each edge has one record: what is promised and what is required there, the checks a
new extension passes, where each extension stands, the edge's concerns and its roadmap. An edge
things attach to keeps one sidecar per extension, holding where that extension's integration lives
and its result for every check. The shape is the format shelf beside the skill; the maintainer
script holds every live record and sidecar to it.

**The record informs; the integration is elsewhere.** A record lives in the instance half, under
`docs/edge/`, and nothing an integration needs to work is read from it: the integration is code and
configuration in its own home, core where it ships, and the record names it *(the user,
2026-10-10)*. So a record may describe core, and core never depends on it. A recipient keeps its
own edges; this tree's records do not ship. Text a recipient meets about an edge — the front page,
an install guide — is derived from the record.

**The checks are the record's, the act is the skill's.** A record's `Extending` lists the checks
every extension passes, as a ticket lists its criteria; the skill's *Extend* goal is the
instruction to build an extension to the contract, pass those checks live, and write the sidecar.
Because every sidecar answers every check by name, a new extension is held to the same checks as
those before it, and a check added later shows at once as unanswered in every sidecar.

**A landed change writes its record in the same commit.** The occasion that most changes an edge
is a landing — a promise, a validator or a check, changed by delivered work — and a
live observation is made in the same work. Both reach `/verify` as an installed rule, E4, since
holding landed work to what governs it is where the occasion is read; without it the record would
be written only at alignment and in maintenance, and fall behind every landing *(the user,
2026-10-10)*.

**Maintenance fits `/maintain`'s model.** A record is of the code and configuration it names, so
when a pass's scope moves a named part the record is re-read against it, and a broken promise is
reported as drift. That duty reaches `/maintain` as an installed block, beside the check that
holds the form. Re-observing is live work and never a maintenance pass's.

**An observation keeps its date, and nothing marks it stale** *(the user, 2026-10-10)*. Its date,
beside the history of the code it watched, already says what it is worth; marking results stale
when a named part moved would cost a judgment at every landing and lose real observations, and
only the next live check acts on age, which runs when an extension is deliberately re-checked.

It is **installed**. A tree without it keeps no edge records; the parts table below is what an
installer adds and an uninstaller removes.

**Who decided each rule.**

| rule | decided by |
|---|---|
| E1 — the records are checked by `edges.py` | the user, 2026-10-10, owed to `/maintain`'s M1 |
| E2 — a record is held to what it names | the user, 2026-10-10: the maintenance rule fits maintenance |
| no staleness marking: an observation keeps its date | the user, 2026-10-10 |
| E3 — a plan is challenged against the edges it touches | the align skill's own text, moved here 2026-10-10 |
| E4 — a landed change at an edge writes its record, a live observation its sidecar | the user, 2026-10-10 |
| an edge is met by consumers and extenders, plugin-like shapes included | the user, 2026-10-10 |
| the record in `docs/edge/`, informing and never depended on | the user, 2026-10-10 |
| the general checks in the record, each extension's specifics in a sidecar | the user, 2026-10-10 |
| `Contract`, `Invariants` with inline validators, `Concerns`, `Roadmap`, the three statuses | with the selected skills, 2026-09-05 |

## Moments

| moment | instructed by | kind, and why |
|---|---|---|
| establishing an edge's record, or populating it from docs, tests and code | `.agents/skills/edge/SKILL.md` | |
| writing a record or a sidecar to its shape | `.agents/skills/edge/EDGE-FORMAT.md` | |
| attaching an extension and passing the record's checks live | `.agents/skills/edge/SKILL.md` | |
| passing the checks again for an extension that changed upstream | `.agents/skills/edge/SKILL.md` | |
| noticing that an extension changed upstream, a host's new version | — | not yet |
| checking a change against the edges it touches, when asked | `.agents/skills/edge/SKILL.md` | |
| writing a record when a change at its edge lands | `.agents/skills/verify/SKILL.md` | |
| writing a live observation of an extension into its sidecar | `.agents/skills/verify/SKILL.md` | |
| challenging a plan against an edge's record | `.agents/skills/align/SKILL.md` | |
| validating code, tests and derived text against a record | `.agents/skills/edge/SKILL.md` | |
| deriving text for a consumer or an extender | `.agents/skills/edge/SKILL.md` | |
| checking live records and sidecars against the shape | `.agents/scripts/gw/edges.py` | |
| re-reading a record when a file it names moved | `.agents/skills/maintain/SKILL.md` | |
| writing an installation-edge change's line as it is made | — | not yet |
| installing this mechanism into a tree, with the rest of core | `.agents/scripts/gw/harness.py` | |
| removing this mechanism from a tree | — | not yet |

## Install adds, uninstall removes

| part | where |
|---|---|
| instruction file | `.agents/skills/edge/SKILL.md` |
| format shelf | `.agents/skills/edge/EDGE-FORMAT.md` |
| this doc | `.agents/mechanisms/edge/edge.md` |
| its rules file | `.agents/mechanisms/edge/edge.rules.md` |
| the maintainer | `.agents/scripts/gw/edges.py` |
| the maintainer's tests | `.agents/scripts/gw/test/test_edges.py` |

## Relies on, and does not own

| part | where | owner |
|---|---|---|
| test harness | `.agents/scripts/gw/test/repository.py` | `mechanism-shape` |
| the installer | `.agents/scripts/gw/inject_rules.py` | `mechanism-shape` |
| the pass that re-reads a record | `.agents/skills/maintain/SKILL.md` | `maintain` |
| the status vocabulary a record's aggregation sections keep out | `.agents/skills/ticket/TICKET-FORMAT.md` | `ticket` |
| the challenge's heading in `/align`, where E3 is installed | `.agents/skills/align/SKILL.md` → "### Challenge against the Edge records" | `/align`'s own, its mechanism not yet |
| the installed rules' heading in `/verify`, where E4 is installed | `.agents/skills/verify/SKILL.md` → "## Installed from other mechanisms" | `/verify`'s own, its mechanism not yet |
| the method's vocabulary | `.agents/glossary.md` | nobody removable |

## What it produces, and who reads it

- **The edge records** — *what must always hold* — read by whoever plans or builds at an edge,
  through the challenge installed in `/align`; by the skill's *Extend* goal for the checks a new
  extension passes; by `/verify` under E4 when a change at the edge lands; by `/maintain` when a
  file a record names moves; and as the source of every
  text derived for a consumer or an extender.
- **The sidecars** — *what exists* — read by whoever attaches or re-checks that extension, by
  `/verify` under E4, and by `/maintain` under E2; each result is an observation as of its date, never a promise.
- **The maintainer's report** — *what exists* — read by `/verify` through the verification set and
  by `/maintain` under E1. Its exit status is what the set consumes; its JSON is for the person
  reading a failure. It writes nothing.
- **The rules file** — *what must always hold* — read by the installer alone, and by whoever amends
  a rule of this mechanism that another skill reads. Its blocks sit in `/maintain`, `/align` and
  `/verify`.

Nothing else; no index. The records directory is its own register.

## Not yet at the shape

**Two `not yet` rows of its own**, each bound to an open question: noticing a host's new version,
and the installation edge's line written as a change is made.

## What retires this

The system having no edge: nothing consumes it from outside and nothing attaches to it. A harness
installed into other projects across several hosts has both, so the condition does not arrive
while the harness is shared.

## What would show it working, graded by someone who did not build it

Pre-registered 2026-10-10, two graders.

**The session that next attaches an extension at an edge that already has some** grades the
record: did the record and the skill's *Extend* goal suffice to integrate and check it, without
reading the history the record was seeded from? Each time it had to go back to that history, or to
the code, for something the record should have said is a miss, named in the evidence.

**The session that writes the installation edge's record** grades the format: did a promised edge,
with no extensions and a different reader, fit the shape unchanged, or did the format have to be
rewritten to receive it? A format bent only for hosts would show here.
