---
name: conclude
description: >-
  Conclude work session into a session record. Use when a chunk of work wraps up.
---

Conclude todays/last session of work (that may span additional chats/external changes) - everything since the previous session recorded, extracting:
- a brief summary of work done (no need to repeat details already stored into other documentation files), 
- what the session settled, one line each with a reference to where the decision now lives,
- the remaining open questions, with compact reasoning and relevant context. 
- and other things that need continuation.

In addition, use /advise skill questions to describe the session.

Open questions go to their owning document first — durable design pressure to `docs/concerns.md`, a ticket's question into that ticket, a hard-to-reverse trade-off to an ADR — and the session file then cites them rather than restating them. Sessions are never maintained as current, so a question left only here will still look open long after it was answered.

And write it into a markdown file under docs/sessions.

Session conventions, owned here — other skills and the directory README defer to this list:

- Named `docs/sessions/NNNN-<YYYYMMDD>-<name>.md`; take the next number from the directory listing.
- A session is a historical snapshot, never maintained as current. Never rewrite an old one to reflect later delivery — write a new one, or update the owning ticket or contract.
- Nothing links *to* a session, including other sessions. Sessions may link outward.
- Records older than the rolling seven-day window move to `docs/sessions/history/YYYY-MM/` (swept by `/denoise`).
