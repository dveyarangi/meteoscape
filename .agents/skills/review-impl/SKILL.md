---
name: review-impl
description: >-
  Review implementation against its input documentation (ticket, RFC, architecture docs) — match, leakage, doc-caused weirdness. Use after an implementation pass.
---


The goal of this skill is to compare the current work's input documentation (ticket, RFC and architectural docs) and the code and find out:
- How good the code shape matches and represents the documentation?
- Where the code shape went wrong or weird because of underspecification or contradiction in the docs?

Look for architectural or responsibility leakage.

If discrepancies or leakages found, describe them in short and suggest ways to amend documentation or/and code. Do not make changes until requested. In case the cause has big blast radius or is significantly ambiguous, /align with user.

Make sure the errors follow error rules.

Apply /improve-comments rules to groom the comments and check that TODO tags are correct.

Apply /plan-impl and /sync-arch skill rules that you think are useful for this task.