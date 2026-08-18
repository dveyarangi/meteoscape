---
name: impact
description: >-
  Trace the consequences of changing a concept, contract, invariant, behavior,
  or artifact before implementation.
---

Find what actually depends on the subject being shaped, behaving, or meaning
what it currently does.

Do not just search mentions. Follow semantic dependencies until the picture
converges.

Check:

- durable docs and decisions
- product/API behavior
- code and composition
- tests, fixtures, parity/reference readers
- active tickets, concerns, RFCs
- upcoming work likely to depend on it
- historical context, without treating history as something to update

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

Output only:

## Impact
Main blast radius.

## Hidden edges
Non-obvious dependencies or risks.

## Leave alone
Related things that should not change.

## Recommendation
Proceed, narrow, rethink, or postpone, and why.