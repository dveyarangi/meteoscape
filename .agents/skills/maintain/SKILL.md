---
name: maintain
description: >-
  Use to hold a declared scope of the tree in agreement — docs to the
  meta-rules, docs to their implementation, records to their format, every
  fact to one home — and to repair the drift; also to retire an expired straw
  dog or archive a finished record. Drift only: a landed slice is verified,
  not maintained.
---

Mechanism: maintain

One pass over a declared scope. The scope decides which rules apply.

## Hold

- **A1** Hold four things in agreement: docs to the meta-rules and their format; a record to the
  thing it is of, by its kind — one of *what must always hold* repairs the thing, one of *what
  exists* is regenerated from it; live records to their declared format; every fact to one home.
  A due pair comes out one of three ways, by whether a decision stands behind the move: a landed
  decision moved the thing and the record lagged — amend the record; none did — repair the thing
  to the record, or take the question to `/align`; the move touches nothing the record says —
  nothing to change. The kind says which side is right when no decision stands behind the move;
  the landing that moved a file is found by its history.
- **A2** Maintain drift only: a governing side that moved with no landing behind it, or clean
  landings that no longer agree. A landed slice is verified, not maintained.
- **A3** When a governing side moves, re-check what it governs, upper link first: the mechanism
  shape, then a mechanism's doc and rules, then its records. Do not stop at the link you were
  sent for.
- **A4** Read dueness from `maintain.py --check` at the start of every pass. Do not infer it.

## Scope

- **B1** Declare the scope first — the tree, a project, or one work item with its consumers and
  governing docs — and write it into the report.
- **B2** Certify only what you examined; mark nothing checked that was not. Route a finding
  outside the scope to the record that owns its subject — the open question in the store that
  already holds it, else the owning work item, else `/align` — after searching the store, so a
  finding already held is cited, not rewritten.
- **B3** Archive every finished record, whatever scope you declared. The record's format says
  what finished means and where it goes.
- **B4** Re-check every mechanism the check reports due or never maintained, whatever scope you
  declared: its doc against the parts it owns at `parts`; at `output`, in the direction the moved
  file gives — a mechanism shape file, its doc and skill against the shape; one of its own, its
  records against its doc and format — the live ones, and historical ones where a mechanical
  change stays in this tree, never records on a remote board. Where the check names the files that moved, were added or went since
  a mark, read those against the record.

## Judge

- **C1** Decide that a record is finished yourself; scripts move and check form, never decide.
- **C2** Rewrite a straw dog the listing reports due to what is now true; whether it is due is
  the store's to say, how it is rewritten is yours.
- **C3** Before removing a straw dog, rehome what outlives it, children before parent. Write
  what is then true where the block was.

## Repair

- **D3** Preserve the facts an archived record records. Never invent a past fact; never imply a
  later requirement was met at the time.
- **D4** Treat a mechanical repair that stopped partway as unfinished: inspect the files against
  what it reported done and pending, finish under the repair policy, and never report a repair
  that did not finish.

## One home per fact

- **E1** Replace a restatement with a pointer. A summary that points deeper is not a duplicate.
- **E2** Let live records carry duplicate context; their indexes may not.
- **E3** Do not cite a record for architecture in a core document.

## Straw dogs

- **T1** List with `straw_dogs.py docs AGENTS.md local.rules.md .agents README.md`. Any diagnostic fails the run;
  zero straw dogs is clean. A straw dog listed `due` is C2's.
- **T2** Remove one you have judged obsolete with `--remove FILE:LINE --expect <fingerprint>`.
  A straw dog holding a nested one is refused: dispose of the children, scan again.
- **T3** Guess with `--guess` over the scope you declared, and judge each candidate: wrap and
  bind it, or leave the claim it is.

## Installed from other mechanisms

One rule of `/spec`'s, held here by hand until that mechanism is declared and installs it:

- **P4** Before archiving a spec, confirm its surviving agreements have homes, its obligations
  have dispositions, and its open issues keep owners.

<installed by="mechanism-shape">
**R1** Check a record-bearing mechanism's records with its maintainer script — format never
content, live rows only. Where the script is missing, write it: that is the maintenance.

**R2** Compare a mechanism against what governs it with line endings normalised, its evidence
excluded, and installed blocks excluded.

**R3** Move story out of a doc into its evidence.

**R4** Render an index on request; never commit one beside its records. A file listing what other
files each say for themselves is an index, whatever it is called — an allowlist, a register,
a manifest — and each entry belongs at its authored home, wrapped there if provisional.
</installed>

<installed by="ticket">
**P1** A ticket is finished when every acceptance box is checked, the verification box included.

**P2** Close a ticket and its RFC together, in one invocation, and every eligible pair in the same
invocation: `move_doc.py [--dry-run] SRC DST [SRC DST ...]`, into `docs/tickets/done/` and
`docs/rfc/done/`.

**P3** Update the ticket header yourself; the mover changes no checkbox, status, date or prose and
leaves the Git index alone. Treat a refusal as a finding. Repair or deliberately leave what it
reports it cannot rewrite, and say which. Git recovers committed or staged content only.

**P5** Check the ticket records with `tickets.py --check` — format never content, live rows only. A
diagnostic is a finding; repair it under the repair policy.
</installed>

<installed by="questions">
**Q4** Check the question store with `questions.py --check`. A diagnostic is a finding; repair it under
the repair policy. Move each subtree it reports ready for `done/` with `move_doc.py`, every entry
of the subtree in one invocation, into `docs/questions/done/`.
</installed>

<installed by="edge">
**E1** Check the edge records and their sidecars with `edges.py --check` — form, never content. A
diagnostic is a finding; repair it under the repair policy.

**E2** An edge record is of the code and configuration it names. When the scope moves a part that a
record under `docs/edge/` names, re-read what it says of that part. A promise the code no longer
keeps is drift, reported with its evidence and never rewritten to fit.
</installed>

<installed by="product">
**U1** Check the product document with `product.py --check` — form, never content. A diagnostic is a
finding; repair it under the repair policy.
</installed>

## Finish

- **F1** Run the checks in the project's verification set that the scope touched.
- **F2** Report: the declared scope, what was checked, what was repaired and against which
  rule, what moved, the marks written, what remains open and who owns it, and what you did not
  cover.
- **F3** Do not verify landed work; a close needs verification to have already happened.
- **F4** Mark each level you re-checked, as the step that closes it and before the report:
  `maintain.py --mark <mechanism> <level> <outcome>`. Mark nothing you did not re-check. An edit
  made between the re-check and its mark is cleared unread.

<installed by="local">
**L3** The verification set: the project's CI and the harness's record checks, every one green.

```
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run pytest
```

```
uv run python .agents/scripts/gw/tickets.py --check
uv run python .agents/scripts/gw/edges.py --check
uv run python .agents/scripts/gw/questions.py --check
uv run python .agents/scripts/gw/product.py --check
uv run python .agents/scripts/gw/maintain.py --check
```
</installed>

## Marks

The marks' format is [MARKS-FORMAT.md](./MARKS-FORMAT.md).
