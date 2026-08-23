- When explaining, use code shapes and diagrams where it is more demonstrative.


- When reading docs, always check the doc type README.md

## Editor skills

The skill set lives in [`skills/`](./skills/). Cursor loads project skills from `.cursor/skills` and Claude Code from `.claude/skills` — both directory symlinks to `.agents/skills`.

Git for Windows writes `core.symlinks=false` into `.git/config` on clone, so those symlinks check out as text files. After clone, in this repo only:

```
git config --local core.symlinks true
git checkout -- .cursor/skills .claude/skills
```

Windows needs Developer Mode (or an elevated prompt) for Git to create the directory link. If checkout still yields a file, delete it and run `mklink /D .cursor\skills ..\.agents\skills` (likewise for `.claude\skills`).