# Installed harness

**The real skill files live in [`skills/`](./skills/).** Loaders are directory links to that folder:

- Codex — reads `.agents/skills` natively; no link needed.
- Claude Code — `.claude/skills` → `../.agents/skills`
- Cursor — `.cursor/skills` → `../.agents/skills`

The links belong to each clone and are never committed. Both are required: Claude Code and Cursor
read only their own directory; Codex reads `.agents/skills` natively and needs none. `/harness`
makes them, or hands the person the exact elevated command where the platform refuses to create
one; a junction is never a substitute, since nothing sees through it.
A fresh clone has no links until `python .agents/scripts/gw/harness.py . --links` runs in it,
which needs no source and no network.

## Mechanical support

[`scripts/gw/`](./scripts/gw/) holds what the harness derives and repairs mechanically: `harness.py`
places a ref of the repository into a tree, updates it and checks the copy, `move_doc.py`
closes a ticket and its RFC together and repairs the citations that pointed at them,
`straw_dogs.py` lists and retires straw dogs and guesses where an unwrapped one stands,
`mechanisms.py` says whether a
mechanism's declaration is true, holds core to citing only the painted doors its mechanisms
declare, and renders the register from
[`mechanisms/`](./mechanisms/), `inject_rules.py` installs a mechanism's rules into the skills
its rules file names, and the project's local file last, and takes them out again, `tickets.py` holds every live ticket to the shape
the ticket format shelf declares, `questions.py` keeps the store of open questions — the window,
the wake, the calls and the check, and the hosts' hooks — and `docs_corpus.py` is the one view of the
tree they share. They
run on the standard library alone, and their behavioral tests are in
[`scripts/gw/test/`](./scripts/gw/test/) — inside `.agents/` because they are core: a recipient's first
run of them is how it learns the scripts arrived intact.
