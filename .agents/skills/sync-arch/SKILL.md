---
name: sync-arch
description: Synchronize architecture docs with high-level code shape.
---

I need you to run a all-around check, and make sure that architecture documentation (./docs/architecture.md, ./docs/adrs, ./docs/glossary.md) properly represent the intent of recently modified code. 

Two ultimate goals for this skill :
1) to make sure architecture docs can be converted to the existing code contract shape in one crystal clear way.

2) To make sure code does not contradicts architectural decision and rules.

There are two kinds of possible discrepancies between architecture docs and code:
- Code misinterpreted or ignored architecture, and needs to be amended. Note that in some cases it is not possible because of core inconsistency - this should be discussed with user
- Docs underrepresent desicions that only became clear when manifested in code. In this case the docs deserve amendment.

So the question you should answer first is will it be possible to recreate exact same implementation contract shape from the arch docs, or there are load-bearing contract details, hidden assumptions/decisions othat are in code by not in docs. 

Look for places where architecture misrepresents, contradicts or is blurry about the aspect represented in code. Look for code that encodes important architectural decisions, but underrepresented in the documentation.
There is no need to add low level details, instead look for architectural seams - interfaces, contracts, boundaries, intents and representations.

Do not add any implementation details to architecture, unless are critical for non-trivial solution record.

If there is a tradeoff, doubt or unresolved concern about the task, or if the code is out of sync with architecture in a major way, use /align skill to align with user.