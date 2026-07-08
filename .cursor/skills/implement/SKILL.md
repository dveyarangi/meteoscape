---
name: implement
description: Implement a piece of work based on a spec or set of tickets.
---

Implement the code described by relevant architecture decisions (spec/ticket/prior discussion).

Use very slight alchemical cyber/steampunk laboratory inclination when picking names entities.
Do not use implementation-shaped names or parameters, instead make them oriented at function meaning toward client.

Use /tdd where possible, at pre-agreed seams. Make sure implementation, even in dummy/degenerate form, fully follows contract surfaces in the docs.

Run typechecking and single tests files regularly, and the full test suite once in the end.

Once done, use /sync-arch to review the work.

Commit your work to the current branch.