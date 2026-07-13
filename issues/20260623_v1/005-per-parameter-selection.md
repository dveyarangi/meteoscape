## Parent PRD

`docs/v1-requirements.md`

## What to build

Prove the **per-parameter capability filter**. Configure at least one core parameter so it is declared
by **only one** provider's `Capability`. For a request spanning the 6 product params, the `Arbiter`
resolves each parameter independently: the single-provider parameter is served from the only provider
that declares
it, while the rest come from the primary. This exercises that selection is per-parameter, not
per-request.

**Decision to resolve in this issue (HITL):** which specific core parameter is single-provider for the
demo (config-driven `Capability`). See `docs/v1-requirements.md` (Providers, Open / TBD during build)
and `docs/architecture.md` (Arbiter, Capability).

## Acceptance criteria

- [ ] One core parameter is declared by only one provider (recorded here, config-driven).
- [ ] A 5-product-param request returns that parameter from its sole provider and the remaining
      parameters from the primary.
- [ ] Each parameter's provenance reflects its actual origin provider.
- [ ] Unit + mocked-transport integration tests assert per-parameter routing.

## Blocked by

- Blocked by `issues/20260623_v1/004-second-provider-fallback.md`

## User stories addressed

- User story 6
