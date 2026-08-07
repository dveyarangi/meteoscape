---
name: conclude
description: >-
  Conclude the current chat into a session record. Use when a chunk of work wraps up.
---

Conclude current chat, extracting:
- a brief summary of work done (no need to repeat details already stored into other documentation files), 
- what the session settled, one line each with a reference to where the decision now lives,
- the remaining open questions, with compact reasoning and relevant context. 
- and other things that need continuation.

Open questions go to their owning document first — durable design pressure to `docs/concerns.md`, a ticket's question into that ticket, a hard-to-reverse trade-off to an ADR — and the session file then cites them rather than restating them. Sessions are never maintained as current, so a question left only here will still look open long after it was answered.

And write it into a markdown file under docs/sessions.
Session file should be using naming pattern `docs/sessions/0001-<YYYYMMDD>-<name>.md`, keeping constantly incrementing enumeration — take the next number from the directory listing, don't assume it.
