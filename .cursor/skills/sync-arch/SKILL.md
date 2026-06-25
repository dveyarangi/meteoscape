---
name: sync-arch
description: Synchronize architecture docs with high-level code shape.
---

I need you to run a bit all-around check, and make sure that architecture documentation (./docs/architecture.md, ./docs/adrs, ./docs/glossary.md) properly represent the intent of recently modified code. 

Look for places where architecture misrepresents, contradicts or is blurry about the aspect represented in code. Look for code that encodes important architectural decisions, but underrepresented in the documentation.
There is no need to add low level details, instead look for architectural seams, - interfaces, contracts, boundaries, intents and representations.

Do not add any implementation details to architecture, unless are critical for non-trivial solution record.

If there is a tradeoff or doubt about the task, or if the code is out of sync with architecture in a major way, use /align skill to sync align user.