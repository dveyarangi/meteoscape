# local — this project's rules, installed into core

Machine input for the installer, read by nobody at session time: what this repository answers
and overrides, in the grammar a mechanism's rules file uses. Amend a rule here, then install it
with overwrite; the block in a target is never the place.

| target | anchor |
|---|---|
| `AGENTS.md` | `## Project-local` |
| `.agents/skills/verify/SKILL.md` | `## The verification set` |
| `.agents/skills/implement/SKILL.md` | `During the work, run the checks in the project's verification set, as` |
| `.agents/skills/maintain/SKILL.md` | `## Finish` |

## L1 — what this repository is

- **target** `AGENTS.md`
- **authority** the user, 2026-10-14

<rule>
Meteoscape: a weather coverage-resolution engine served over MCP, Python 3.14 managed by uv.
Terms: docs/glossary.md, this project's own; the method's are .agents/glossary.md's. What each
document owns: docs/README.md.
</rule>

## L2 — the switches

- **target** `AGENTS.md`
- **authority** the user, 2026-10-14

<rule>
commit=auto · push=ask · next-cycle=ask · breakdown=ask · repair=report
</rule>

## L3 — the verification set

- **target** `.agents/skills/verify/SKILL.md`
- **target** `.agents/skills/implement/SKILL.md`
- **target** `.agents/skills/maintain/SKILL.md`
- **authority** the user, 2026-10-14

<rule>
The verification set: the project's CI and the harness's record checks, every one green.

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
</rule>
