---
name: plan-impl
description: Plan implementation for ticket/task at hand
---

- Explore documentation in depth, follow links in it to find all decisions relevant to current task. 

- Establish implementation scope, pinpoint and mention affected boundaries, contracts, ownership. Present main code shapes - especially ones that represent documented boundaries. Present code flows.

- Detect open concern and use /align skill to resolve them with user.

- Major goal of this planning is to find inconsistencies in the pre-planned architecture. Do this diligently. If such inconsistency found, do not stick blindly for architectural decision - instead raise concern with user to resolve it - either in code or in arch docs

- Describe the implementation stages; allocate them accordind to /tdd rules.

- Cover migrations, compatibility, rollout, failure handling, and observability when relevant.


- Map out scope-specific limitation, follow-ups and related out-of-scope concerns.

- Do not leave implementation ambiguities or optionalities, no matter how small - either resolve them or consult with user.

- Record the plan into markdown file in /docs/rfc. Theile should be using naming pattern `docs/rfc/0001-<YYYYMMDD>-<name>.md`, keeping constantly incrementing enumeration.

- DO NOT CHANGE THE CODE!