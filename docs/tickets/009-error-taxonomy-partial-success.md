## Parent PRD

`docs/v1-requirements.md`

## What to build

Make failures and partial results first-class. The `Arbiter` resolves each parameter independently and
**omits** any whose candidates all fault, so a partially-served request returns the **producible
subset** (an unserved parameter is simply absent, never persisted). `project` stays closed — failures
are not Coverage state. The **edge** derives each absent parameter's reason (capable ⇒
`runtime-failure`, else `capability-mismatch`) and raises a whole-request error only when **nothing** is
produced. The MCP adapter maps the taxonomy — `bad-request` (e.g. invalid lat/lon),
`capability-mismatch`, `runtime-failure` — to MCP protocol errors. **nodata** (a successful gap,
`present[i] = False`) is never conflated with failure.

**Already landed at 001 (Phase C):** taxonomy → `ToolError` **stable prefixes**, lat/lon and
unknown-parameter `bad-request` validation, producible-subset serving with whole-request
`capability-mismatch` only when nothing is produced, and nodata → `null` serialization. This issue's
remaining substance: the **edge-derived per-parameter absence reason** (capable ⇒ `runtime-failure`,
else `capability-mismatch`) on partial responses, and the capable-but-all-candidates-fault omission
path (needs 004's fallback machinery — Phase C propagates a lone candidate's `RuntimeFailure` whole).

See `docs/architecture.md` (Failure, nodata, and availability; Error taxonomy) and
`docs/v1-requirements.md` (Errors, acceptance §7).

## Acceptance criteria

- [ ] Invalid input (e.g. out-of-range lat/lon) maps to `bad-request`.
- [ ] A parameter no provider declares maps to `capability-mismatch`; a capable-but-faulting parameter
      maps to `runtime-failure`.
- [ ] A partially-served request returns the producible subset; absent parameters carry the edge-derived
      reason and are never persisted.
- [ ] A whole-request error is raised only when nothing is produced.
- [ ] **nodata** (`present[i] = False`) is returned as data, never as a failure.
- [ ] Unit + mocked-transport integration tests cover each error class and a partial-success response.

## Blocked by

- Blocked by `docs/tickets/003-request-shaping.md`

## User stories addressed

- User story 8
- User story 9
