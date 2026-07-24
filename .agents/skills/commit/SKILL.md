---
name: commit
description: >-
  Rules for committing changes to code repository; Do not commit unless got explicit instruction or permission from user
---

- Look and pending changes; group them by content aligning with origin topic, ticket, rfc or change type (docs/code/cicd).

- Separate implementation and documentation commits; tags them with either DOCS, CODE or CICD.

- In case the file changes belong to several groups, commit the file with the group forming its dominant topic and mention the bleed in that commit's message.

- Do not reference sessions in commit comments, sessions are ephemeral.

- Unless already working in branch or instructed to branch - commit to default branch.

- Always run ruff, pyright and pytests before commiting.

- Do not commit unless got explicit instruction or permission from user.
- Separately, do not push unless got explicit instruction or permission from user.