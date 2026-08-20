---
name: sync-arch
description: Synchronize architecture docs with high-level code shape.
---

I need you to run an all-around check, and make sure that architecture documentation (./docs/architecture.md, ./docs/adrs, ./docs/glossary.md, and the Edge records in ./docs/edge/) properly represent the intent of recently modified code. 

Two ultimate goals for this skill :
1) to make sure architecture docs can be converted to the existing code contract shape in one crystal clear way.

2) To make sure code does not contradict architectural decisions and rules.

There are two kinds of possible discrepancies between architecture docs and code:
- Code misinterpreted or ignored architecture, and needs to be amended. Note that in some cases it is not possible because of core inconsistency - this should be discussed with user
- Docs underrepresent desicions that only became clear when manifested in code. In this case the docs deserve amendment.

So the question you should answer first is whether it is possible to recreate the exact same implementation contract shape from the arch docs, or there are load-bearing contract details, hidden assumptions/decisions that are in code but not in docs.

Look for places where architecture misrepresents, contradicts or is blurry about the aspect represented in code. Look for code that encodes important architectural decisions, but underrepresented in the documentation.
There is no need to add low level details, instead look for architectural seams - interfaces, contracts, boundaries, intents and representations.

Do not add any implementation details to architecture, unless are critical for non-trivial solution record.

Check `./docs/concerns.md` the same way: a concern the implementation has since answered is a finding — the file still claims open pressure that code resolved. Retire it to its owning ADR or architecture section rather than leaving it standing.

For Edge records specifically (format: align skill's EDGE-FORMAT.md): code must not contradict a promise in a `Status: Normative` record, and each invariant's named validator test must still exist and still assert that promise — a missing or drifted validator is a finding, as is a promise marked **⚠ unguarded** in a Normative record.

If there is a tradeoff, doubt or unresolved concern about the task, or if the code is out of sync with architecture in a major way, use /align skill to align with user.