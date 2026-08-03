---
name: plan-impl
description: Plan implementation for ticket/task at hand
---

- Explore documentation in depth, follow links in it to find all decisions relevant to current task. Find our which documented boundaries are involved, and whether implementation challenges them.

- Establish implementation scope, pinpoint and mention affected boundaries, contracts, ownership. Present main code shapes - especially ones that represent documented boundaries. Present code flows.

- Detect implementation challenges and use /align skill to resolve them with user.

- If you see a concern, first check deeper how the existing architecture documentation describes it - it most probably already does. Read architecture.md ARDs and concernsmd for this.

- Major goal of this planning is to find inconsistencies in the pre-planned architecture. Do this diligently. If such inconsistency found, do not stick blindly for architectural decision - instead raise concern with user to resolve it - either in code or in arch docs.

- Another major goal is to make sure that resulting RFC does not leave implementation ambiguances. Meaning there is only one way to implement the RFC. Do not rely on information in the session or architecture files - if a fact is relevant and shaping the implementation - it should be accented and referenced in RFC.

- Describe the implementation stages; allocate them accordind to /tdd rules. Look at stages to make sure each of them keeps the tests green; in case that would take too much temporary effort, allow red, note about test status and compact reason for it.

- Map out scope-specific limitations, follow-ups and related out-of-scope concerns.

- Prefer reuse and reduction of existing nouns, verbs and adjectives; when adding shape - make sure documentation supports it, if in any doubt - /align with user.

- If planned code includes a temporary solution that is dissolved by future development, add RFC instruction to append TODO comment to code that flags this. Otherwise code changes can start relying or considering the temporal code, which can be hard to disentangle later.

- In overall, always consider future development and potential code reuse when selecting code shapes.

- Cover migrations, compatibility, rollout, failure handling, and observability when relevant.

- Do not leave implementation ambiguities or optionalities, no matter how small - either resolve them or consult with user.

- Record the plan into markdown file in /docs/rfc. The file should be using naming pattern `docs/rfc/0001-<YYYYMMDD>-<name>.md`, keeping constantly incrementing enumeration.

- DO NOT CHANGE THE CODE!