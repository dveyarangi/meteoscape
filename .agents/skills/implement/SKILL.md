---
name: implement
description: Implement the agreed work into code, following its governing docs.
---

Implement the code described by relevant architecture decisions (spec/ticket/rfc/prior discussion).

Pick entity names in vibe with the project glossary.
Do not use implementation-shaped names or parameters; orient them at the function's meaning toward the client.

Use /tdd where possible, at pre-agreed seams. Make sure implementation, even in dummy/degenerate form, fully follows contract surfaces in the docs.

Make methods behind main architectural boundaries clear - they should read almost as a story explaining the boundary logic, with separate concerns extracted to properly named sub-methods. Also, in general, prefer to split submethods by responsibility. 

The code should read as a story. Make sure the main process appears first in the file, where possible, and main boundaries' implementation reads through entities, interfaces and submethods used as nouns, adjectives and verbs.


In case of temporary code added as intermediate scaffolding that is going to change/go away in future iteration, mark it so in docstrings.

Make sure comments adhere to /improve-comments rules

Run typechecking and single tests files regularly, and the full test suite once in the end.

Once done, if relevant, use /review-impl and /sync-arch to review the work.

Do not commit your work until requested.