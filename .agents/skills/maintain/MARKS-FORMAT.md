# Marks format

This shelf owns the format of the marks, the maintain mechanism's one record:
`docs/mechanisms/maintenance.md`, a heading, a line pointing here, and two tables, written only by
`maintain.py --mark`.

| mechanism | level | fingerprint | date | outcome |
|---|---|---|---|---|

| mechanism | level | file | fingerprint |
|---|---|---|---|

- The first table: one row per mechanism per level; `level` is `parts` — the doc against the
  parts the mechanism owns — or `output` — its records against its doc, rules file and skill,
  and its doc and skill against the mechanism shape's, the shape's outputs read one mechanism at
  a time in that mechanism's row. `fingerprint` is 64 lowercase hex, of everything the level was
  checked against, and alone decides whether the level is current; `date` is `YYYY-MM-DD`;
  `outcome` is `amended` — the record, to a landed decision — `repaired` — the thing, to the
  record — or `nothing to change`. `rules` was a level until 2026-10-11, the doc against the
  meta-rules; its rows left the marks by hand at the landing that retired it, the one write not
  `--mark`'s.
- The second table: one row per file a level was checked against, with that file's fingerprint,
  so a level falling due names the files that moved, were added or went. A first-table row with no
  files was written before a mark kept them: it reads, and when due names none.
- A row whose mechanism is no longer declared is dropped at the next mark, with its files. Rows are
  sorted by mechanism, then level, then file.
- Read by `--check` at every pass; a malformed row of either table, or a file kept for a level with
  no row, fails the check and refuses every mark until it is repaired.
- In a recipient the mechanisms that came with core are maintained where core is made: the check
  leaves them out and a mark refuses them.
