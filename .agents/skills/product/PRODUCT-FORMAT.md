# Product document format

One document per project, a living record at `docs/product.md`, the home of the decisions taken
under the purpose root. Tier 2: read by a person deciding what the project is for, by the agent
landing an answer, and by `product.py`. Nothing removes an answer: it is retired in place, its id
never given again. Its history is git's.

## Sections

- **Pains** — what hurts, numbered. A pain has no closed state: answers are added to it, and none
  of them closes it.
- **Goals** — what must not be lost, each `G<n>` in its bold lead.
- **Causes** — why the pains happen, each `C<n>` in its bold lead.
- **Answers** — a table, one row per answer, under the heading `## Answers`.

## The answers table

The first cell of an answer row opens with its bold lead, `**A<n> <name>**`, and may go on to say
what the answer is:

```
| answer | causes | 1 | 2 | G1 | waits on |
|---|---|---|---|---|---|
| **The shared exploration space** | | | | | |
| **A1 The question store** — open questions as a tree, each with its lean | C3, C4 | ● | ● | | |
```

- **The id** is `A` and a number, never renumbered and never given twice. A replaced answer keeps
  its id; a new answer takes the next.
- **The name** is what a trace link quotes, word for word. Renaming an answer means re-quoting
  every link that names it.
- **A group heading** is a row whose first cell alone is filled; it is no answer.
- **The pain and goal columns** mark with `●` what the answer serves; **causes** names the causes
  it acts on.
- **Waits on** is empty for a decided answer, which points nowhere: its coverage is read from the
  questions that realize it. An answer not chosen yet holds a straw dog bound to the purpose
  question it waits on.

No column holds a status: coverage is rendered by `product.py --coverage`, never written.
