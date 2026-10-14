# The development method

The vocabulary the harness itself is written in — the terms its skills, rules, records and checks
use. It travels with `.agents/`. A project's own domain vocabulary belongs in `docs/glossary.md`,
which the project owns outright; when a term here and a term there collide, the project's wins
inside its own domain and this one wins about the method.

These definitions are a working vocabulary for alignment; a proposed distinction does not by
itself authorize new process machinery.

## Language

**Harness**:
The development instructions and supporting mechanisms through which projects define, implement, verify and maintain software, including the harness itself.

**Mechanism**:
A part of how the work gets done, on which other work relies, together with its instructions, producers, consumers, checks and records. It owns one or more instruction files, each a skill no other mechanism owns, and may span many other files. What the project produces is not one.

**Skill**:
A mechanism's own instruction file, invocable and identified by its purpose and conditions of use. A skill may also host rules installed into it by mechanisms that do not own it.

**Straw dog**:
Text or code an open question's answer will change, wrapped in a `<straw-dog>` bound to that question at the moment it is written. Not a question itself: provisional text that waits on one. Unwrapped, it is drift the enumerator cannot see. What no open question would change is a claim.
_Avoid_: temporary statement, temporary, placeholder, stub, interim, hack.

**Rules file**:
The one authored home of the rules a mechanism installs into skills, its own included: `<slug>.rules.md` in its own directory, machine input for the installer, read by nobody at session time.

**Installed block**:
A mechanism's rules as they reach a skill: one `<installed>` block per mechanism per target, written by the installer from the rules file and compared against it, never edited where it sits.
_Avoid_: injected pointer, copy.

**Part**:
A file or asset a mechanism owns: installing the mechanism adds it, uninstalling removes it. What a mechanism leans on but would not take with it is relied-on, named with its owner, and not one of its parts.
_Avoid_: component, piece, asset.

**Moment**:
An occasion at which a person acts on a mechanism. Each is either instructed, or carries a stated kind of absence. If nobody acts, it is not a moment.

**Doc**:
The record of why a mechanism's instruction is what it is — the documentation of a mechanism. Never the same file as the instruction. Of the kind *what must always hold*.
_Avoid_: manual, reference, spec as a name for this.

**Documentation**:
The role a doc plays for an implementation: what it must do and why. A mechanism's doc for its skill and scripts; a project's architecture for its code. A role, not a kind: documentation is of the kind *what must always hold*, and a disagreement with its implementation is repaired at the implementation.
_Avoid_: spec, manual.

**Implementation**:
What a documentation describes and must agree with: a mechanism's instruction file and scripts; a project's code.
_Avoid_: source; product as a synonym.

**Record**:
What a mechanism writes and keeps under a declared format, live until archived: a ticket, an RFC, a session record, the marks. An entry is one row of a record that holds many. Being a record says under what format a thing is written, a second axis beside its kind: the kind is the format's to declare.
_Avoid_: log.

**Mark**:
The row a maintenance writes when it has re-checked a mechanism at a level: the fingerprint of what it checked against, the date, and the outcome. Only the maintenance that finished the re-check writes one; no edit to a doc is a mark. Of the kind *what exists*.
_Avoid_: timestamp, last-checked, checkpoint.

**Due**:
Said of a mechanism at a level when what governs it has moved since its mark, or it has none — *never maintained*; and of a straw dog when the answer its question waited on has landed, or the question no longer stands. Derived at every look, never stored.
_Avoid_: stale, dirty, pending.

**Evidence**:
The record of why a doc is what it is: what was tried, what was refuted, what it cost, what it used to be. One per mechanism. Evolution belongs here; provenance does not. Of the kind *what happened*.
_Avoid_: sidecar, notes, history, appendix. *Sidecar* describes a file's position, never its contents.

**Provenance**:
Who decided a rule and when, carried inline on the rule itself. It is not evidence and does not move to the evidence file: attribution at the moment of reading is what makes a rule challengeable. A part of a rule, of no kind of its own.

**Authority**:
Who may establish, amend or waive a rule. Stated on the rule, inline, as its provenance; the repair policy says what a maintainer may do with the rest. Separate from delivery tier and from evidence of effectiveness.
_Avoid_: strict rule, working rule, rule strength.

**Tier**:
How a thing reaches a session — forced into context, asked for, or reachable only by someone who already knows it exists. Reachability, never importance or read-frequency.

**Index**:
A compact list of a register's records, derived from them on request rather than kept beside them. Enough per record to decide whether to open it, and never a second home for what the record already says. Of the kind *what exists*.
_Avoid_: digest, summary, table of contents.

**Core**:
The accepted shared method and supporting assets governed at their canonical source.

**Project-local**:
A project's own answers and overrides, authored once in its local rules file beside the entry file and reaching core files only as the local block the installer writes there, after every mechanism's. An override names the rule it overrides and is what the reader follows.

**Install** *(of core)*:
Placing a ref of core into a tree that is not core's own repository, from a fresh clone of that repository and never from a working tree; an update is the same over a tree that already holds one, and a check compares a copy against the ref its entry file announces. The mechanism that does all three is `harness`.
_Avoid_: deploy, sync, distribute, port.

**Edge**:
Where the system meets someone outside it: a consumer of what it promises, or an extender attaching to it — a host and its integration, a recipient with its own mechanisms. Each edge has one **edge record** under `docs/edge/`: what is promised and required there, the checks a new extension passes, where each extension stands. A seam between two of the system's own parts is the architecture's, never an edge.
_Avoid_: surface, boundary as names for this.

**Extension**:
One thing attached at an edge — a host, with the integration that reaches it — kept in a sidecar of its edge record, which holds where the integration lives and its result for every check the record names.
_Avoid_: plugin, adapter.

**Installation edge**:
The edge between core and a recipient. Everything about the core–instance interaction an instance must know to integrate core, customise it and stay coherent across core changes: a rule id, a target and its anchor, a script's path and command, a skill's name, the announce form, and a behaviour a recipient's files rely on. What a recipient never meets — a skill's body, a declaration's prose, a script's internals — is not on it.
_Avoid_: API, surface, interface as names for this.

**Release**:
One publish of core to its own repository, carrying a note written for an instance: what moved on the installation edge, from where to where, and what an instance amends. The note is derived at the publish from the edge's engineering record, which every edge change writes its line in as it is made. A recipient reads the notes standing between its ref and the latest before deciding to take them.
_Avoid_: version, cut, ship, distribution.

**Recipient**:
A tree that received core by install. Its entry file's announce line names the repository and the ref it came from, `<repository>@<ref>`; the one tree whose line carries no `@` is core's own repository, the origin, and is never installed into.
_Avoid_: instance as a name for the tree, consumer.

**Host**:
The program that runs an agent's session and reads the tree for it — Claude Code, Codex, Cursor.

**Loader link**:
A link from the place a host looks for skills to `.agents/skills`, so every host reads the one copy.

**Painted door**:
A path under `docs/` that a mechanism declares as where its records live — the directory, or the one file that is a record — and thereby reserves in every recipient: core may name it, and a record written there makes it. Some arrive with content, where the owning mechanism declares what the record says before anything has happened in it; the rest come into being when the first record is written. A particular record inside one is a document, not a painted door.
_Avoid_: place, path convention.

**Leak**:
A citation from core to a document only the instance has. A painted door is not one; a particular record behind it is.
_Avoid_: reach, dangling link, cross-reference as names for this.

**Open issue**:
An unresolved problem, question or risk that needs a disposition. It is unresolved subject matter, not a synonym for a spec, ticket or RFC; its current owning record holds it.
_Avoid_: issue as a generic name for every development document.

**Spec**:
A change-scoped definition of intended capability, scope and governing behavior from which delivery work can be derived. Its enduring agreements belong in maintained governing documents; its eventual historical status does not itself establish that the change was delivered. Of the kind *what it intends to become*.

**Architecture**:
The maintained description of system responsibilities, load-bearing seams and governing constraints, with the status of current and agreed target behavior explicit.

**Capture**:
Recording an issue with enough context to preserve its meaning and an identifiable owner. Capture does not by itself authorize investigation, implementation or a new mechanism.

**Routing**:
Selecting the existing record or kind of work that should own an issue, and the next applicable development stage.

**Decomposition**:
Dividing agreed work into independently verifiable parts while preserving its scope, contracts and dependencies.

**Pace**:
Which authorized work proceeds now, pauses, or awaits a decision. Pace is distinct from the scale or document type of the work.

**Execution step**:
The execution of a single skill. It has an input state, an immediate purpose, an expected result and a reassessment boundary at its end, and need not complete its owning ticket.

**Turn**:
One agent reply, from the user's message to the reply's end. A turn holds at most one execution step; a step may span turns.

**Uncharted**:
A question whose home in the question store the agent cannot settle, put to the person until they say where it belongs. A question the agent can word and place is opened, not uncharted; work the agent knows how to do is a process, not a question.

**Banter**:
A message that asks nothing of the work — no question about the project, nothing to do or decide — answered by a reply that writes nothing and settles nothing. A message the agent doubts is not banter.
_Avoid_: unplaced, nowhere, new as names for this.

**Archived record**:
A historical account retained after its active role ends, with its disposition explicit; of the kind *what happened*. Current work should be understandable from maintained sources without requiring that record; historical investigation and mechanical maintenance may still reach it.

**Ticket**:
A tracked unit of agreed work with an intended outcome and observable completion criteria, minted from the body of the question it answers once the work's form is seen. It holds what is actual for the work; a decision lands where it is made, not in the ticket. Of the kind *what it intends to become*: spent when its criteria hold.
_Avoid_: dossier, decision log, history as names for a ticket's contents.

**HITL ticket**:
A ticket whose progress requires a human decision or interaction. Its scope may still be undecomposed, but HITL does not itself specify size or maturity; investigation can reveal a need for a spec and multiple delivery tickets.

**RFC**:
An implementation proposal or agreed plan for an owning ticket, grounded in the governing architecture and contracts. Its existence alone does not mean its proposal has been accepted. Of the kind *what it intends to become*.

**Shape**:
Whatever is currently under consideration, held between an idea and a thing: it has taken enough form to have a context and a structure, and is not yet exhausted by any one realization. A concept, contract, invariant, behavior, rule, method or artifact can each be held as a shape.

- Idea — "historical forecasts should stay comparable." No form yet; `/align` owns it.
- Shape — "historical forecast issues must remain independently addressable by (location, valid_time, issue_time)."
- Thing — "forecasts are stored in the `forecast_hourly` collection." One realization.

Being a shape says nothing about being load-bearing. An implementation method is a shape, and can be a rich one that repays `/impact` and `/discover`, while remaining local to the code it lives in.
_Avoid_: form, construct, entity.

**Seam**:
A boundary across which a producer supplies behavior, information or an artifact that a consumer relies upon.

**Load-bearing seam — proposed definition**:
A seam across distinct responsibilities whose contract determines a promised outcome, authority, data meaning or integrity, compatibility, or recovery beyond either side's implementation-local choices. A change that appears valid at one end can invalidate the other end or their shared guarantee.

**Kind of statement**:
What a written sentence of the method is, told apart by one test each: an **instruction** says what to do — a rule, with a moment and an outcome; a **principle** says what to prefer when it is unclear what to do; an **invariant** says what must hold; a **definition** says what a word means; a **classification** says where a thing goes when it is unclear what it is. A sentence is of one kind; which kinds a reply marks, and how, is the entry file's.

**Principle**:
What to prefer when it is unclear what to do: a preference under uncertainty, written as *prefer A over B* and applied by judgement. It names no occasion and no outcome, so it never fires and is never a rule failure: a principle that "did not fire" is a rule missing. Its home is the entry file's general section, a mechanism's doc, or this glossary, and it carries a name there — the bold lead of its sentence — by which it is cited; in an instruction file it appears only as the pointer behind a rule.
_Avoid_: rule, guideline as its name.

**Rule**:
An instruction with a moment — the occasion, in the words a person would use for it — and an outcome that can be checked afterwards. Its home is a rules file, installed at the tier its moment reads, citing the principle behind it. A judge's invocation is a rule; what the judge judges by is a principle.
_Avoid_: principle, for an instruction that has no moment.

**Invariant**:
What must hold of a thing at all times, written in a record of the kind *what must always hold*. Its violation is a defect repaired at the thing, never a rule failure; it is not a preference and is not marked as a principle.

**Definition**:
What a word means, held by a glossary — this one for the method, the project's for its domain. A definition authorizes no machinery and is marked in a reply only as the footing a claim rests on.

**Classification**:
A sort with a claim of completeness and a test that says where a thing goes when it is unclear what it is. One an agent applies by judgement carries a name by which a reply cites it — *kind of record*, *kind of statement*, *kind of turn*, *kind of moment*, *tier*; one a script reads is an enum in its format and needs none.

**Kind of record**:
What a record is by its source of truth, on two axes: which side is right when the record and the thing it is about disagree — the record, the thing, or neither — and whether the record's authority expires once the thing reaches it. Four kinds: **what it intends to become** — the record, until reached; the thing moves toward it and the person refines it, and it is spent when the thing matches it; **what must always hold** — the record, standing; the thing is repaired to it, and it changes only by decision; **what exists** — the thing; the record is brought to it, regenerated where a script can and rewritten by hand where none can; **what happened** — neither, the referent being past; never repaired. The test between the first two, both written before the thing obeys them: the first expires when reached, the second keeps governing. A format declares the kind of its records once, as their authored home, and every record an agent edits carries it visibly on itself — the mark at the thing — so the agent meets it in context before adding what the kind refuses; a document without a format carries it on itself alone, and a record only a script writes carries none.

**Whiteboard**:
The body of the question a task stands on, where everything bearing on the task is written until enough has gathered to see its form; then sorted into records of their kinds. It is of no kind, maintenance does not hold it, and a ticket is minted from it, never before it. A decision does not wait on it: it lands as it is made, and only one with nowhere to land yet waits in the body's `## Decisions` list.
_Avoid_: draft as a record type, scratch, notes.

**Kind of turn**:
What a turn is, said before its reply is drafted: on a question, a new question, a process, uncharted, or banter. The classification is Q1's, in the questions mechanism's rules file.

**Kind of moment**:
What a mechanism's moment carries: instructed by another mechanism, instructed from the wrong home, unowned by design, or not yet. The classification is the mechanism format's.

**Meta-rule**:
An instruction on how instructions are made, changed, checked or maintained — the mechanism shape's alone, held in the shape's own skill, and installed from its rules file where another file reads it. A principle that bears on everything, instructions among them, is a meta-principle: meta too, and the entry file's own.

**Tier 1**:
Context supplied to the agent at the relevant occasion without a separate retrieval action. Intended Tier 1 placement and observed delivery are distinct facts.

**Tier 2**:
Content retrieved when a Tier 1 trigger or reference makes it relevant. A request to read content does not itself establish retrieval.

**Rule slice**:
The selected portion of governing instructions relevant to a particular task, stage or event, retaining its source and applicability.

**Delivery evidence**:
An observation supporting that selected content reached the agent's context. It is distinct from a file existing, a hook emitting output, or evidence that the instruction was followed.

**Derived work**:
An artifact or behavior produced or maintained under a governing rule or contract, whose validity may need reassessment when that source changes.

**Reconciliation**:
Resolving differences between independently evolved states against their origins and governing agreements, retaining unresolved differences until they have a disposition.

**Entry contract**:
The instructions every host supplies at session start, versioned, and announced verbatim by the session's first reply as evidence of delivery.

**Autonomy switch**:
A named setting a project gives a value to, deciding whether an action proceeds or waits for a human; skills defer to it.

