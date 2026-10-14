---
name: product
description: Keep the project's product document — the pains it relieves, its goals, the causes and the answers — and see how much of each answer is built. Use when a decision about what the project is for lands as an answer, when writing or reading the product document, or when asked which answers are built, being built, or not started, or what each queued ticket builds and which answers no ticket does.
---

Mechanism: product

# The product document

The project's account of what it is for lives in `docs/product.md`, in the shape of
[PRODUCT-FORMAT.md](./PRODUCT-FORMAT.md): pains, goals, causes, and answers, each answer an id
never renumbered and a name.

## Goals

1. **Keep the document.** Land a decided answer as a row with the next free id and a name, or, where
   a row waited on its question, empty that row's *waits on* cell; retire
   an answer rather than renumber it, and give a replacement a new id. A row whose answer is not
   chosen waits on its purpose question, bound to it. A pain is never closed.
2. **Link the work.** A question that builds an answer carries its trace link, by id and name
   word for word: `questions.py realize q-N 'A7 "<name>"'`, or `derived` for one that realizes
   none. Its sub-questions carry it without writing it.
3. **See coverage.** `product.py --coverage` renders each answer as absent, in progress or present,
   read from the questions that realize it. Coverage is never written into the document.
4. **See the queue beside it.** `product.py --queue` renders what each live ticket realizes and the
   answers left out — neither present nor realized by a ticket — under each pain and goal they
   serve, for the person ordering the work. It ranks nothing and is never written into the queue.

Check the document's form with `product.py --check`.
