---
name: code-review
description: >-
  Rules for reviewing code changes.
---


The goal of this skill is to compare current works input documentation (ticket, RFC and architectural docs) and the code and find out:
- How good the code shape matches and represents the documentation?
- Where the code shape went wrong or weird because of underspecification or contradiction in the docs?

Look for architectural or responsibility leakage.

If discrepancies or leakages found, describe them in short and suggest ways to amend documentation or/and code. Do not make changes until requested. In case the cause has big blast radius or is significantly ambiguous, /align with user.

Apply /plan-impl and /sync-arch skill rules that you think are useful for this task.