# product — rules installed into skills

Machine input for the installer, read by nobody at session time. Amend a rule here, then
install it with overwrite; the block in a target is never the place.

| target | anchor |
|---|---|
| `.agents/skills/maintain/SKILL.md` | `## Installed from other mechanisms` |
| `.agents/skills/align/SKILL.md` | `### Land resolutions as they are made` |
| `.agents/skills/questions/SKILL.md` | `## A raised question` |

## U1 — the product document is checked by its maintainer

- **target** `.agents/skills/maintain/SKILL.md`
- **authority** the user, 2026-10-13

<rule>
Check the product document with `product.py --check` — form, never content. A diagnostic is a
finding; repair it under the repair policy.
</rule>

## U2 — a decided purpose question is allocated in one step

- **target** `.agents/skills/align/SKILL.md`
- **authority** the user, 2026-10-13 and 2026-10-14

<rule>
When a question under *What is this project for?* is decided with something to build, do three
things in one step:

1. With `/product`, write the answer into the document: a row that waits on this question has
   its *waits on* cell emptied; otherwise a new row takes the next number.
2. Close the question against that row.
3. Open the question of how to build it in the *How is this project built?* branch, under the
   question it belongs to, and give it its trace link with `questions.py realize`, naming the
   row's number and name.

A decision that changes, replaces or retires an answer is written by `/product` the same way.
</rule>

## U3 — a question opened right under the structure root says what it realizes

- **target** `.agents/skills/questions/SKILL.md`
- **authority** the user, 2026-10-13

<rule>
A question opened right under *How is this project built?* gets its trace link at once: the
answers it realizes — `questions.py realize q-N 'A7 "<name>"'` — or `realize q-N derived` for
none.
</rule>
