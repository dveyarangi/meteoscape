---
name: impact
description: >-
  Use when asked to check the impact of an issue or its slice.
  Trace the consequences of changing a concept, contract, invariant, behavior,
  or artifact before implementation.
---

Mechanism: not yet

Find what actually depends on the subject being shaped, behaving, or meaning
what it currently does.

Do not just search mentions. Follow semantic dependencies until the picture
converges.

Check:

- durable docs and decisions
- product/API behavior
- code and composition
- tests, fixtures, parity/reference readers
- active tickets, open questions, RFCs
- upcoming work likely to depend on it
- historical context and records; history is maintained mechanically like everything else (`/mechanism`, *Mechanical by construction*), not exempted from repair

Distinguish:

- must change
- must verify
- may simplify
- hidden risk
- historical only
- probably unaffected

Look especially for assumptions shared across docs, code, and tests: internal
agreement does not prove external correctness.

Challenge the proposed change too:
- is it solving a demonstrated problem?
- can it be narrower?
- does it introduce a general abstraction?
- if so, what second materially different concrete shape justifies it?

The assessment is these four sections and nothing else. That governs its shape, never the
turn: called from another skill, hand them back and carry on with the step that called.

## Impact
Main blast radius.

## Hidden edges
Non-obvious dependencies or risks.

## Leave alone
Related things that should not change.

## Recommendation
Proceed, narrow, rethink, or postpone, and why.
