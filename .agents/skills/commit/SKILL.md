---
name: commit
description: >-
  Rules for committing changes to the code repository. Never commit without explicit instruction or permission from the user.
---

- Commit the work in current session only. Do not commit changes of other session that might represent a work in progress. When in doubt, ask user.

- Look at pending changes; group them by content aligning with origin topic, ticket, rfc or change type (docs/code/cicd/skills).

- Separate implementation and documentation commits; tag them with either DOCS, CODE, CICD or SKILL. Changes to the agent skills corpus take SKILL.

- In case the file changes belong to several groups, commit the file with the group forming its dominant topic and mention the bleed in that commit's message.

- Do not reference sessions in commit comments, sessions are ephemeral.

- Unless already working in branch or instructed to branch - commit to default branch.

- When committing a code change, first run the checks that repository defines for itself — its linter, its formatter in check mode, its type checker, its tests. Pure doc changes need none of them.

- Do not commit without explicit instruction or permission from user.
- Separately, do not push without explicit instruction or permission from user.

<project-local>
The checks are the same gate set CI runs → [cicd.md](../../../docs/cicd.md): `ruff check`, `ruff format --check`, `pyright`, `pytest`.
</project-local>