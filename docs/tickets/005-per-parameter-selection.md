# 005 — Per-parameter selection

- **Status:** Planned
- **Depends on:** [004 — Second-provider fallback](./004-second-provider-fallback.md)
- **Outcome:** One response assembled from different winning providers by parameter.

## Parent PRD

`docs/v1-requirements.md`

## What to build

Prove the **per-parameter capability filter**. The multi-node Coverage **assembly** itself already landed
in [002b](./002b-derived-wind-calculator.md) (the top Arbiter stitching disjoint single-parameter winners,
first forced by the derived-wind Calculator beside the canonical params); this ticket adds no new assembly
machinery — it exercises that same path with **competing providers**. Configure at least one core
parameter so it is declared by **only one** provider's `Capability`. For a request spanning the 6 product
params, the `Arbiter` resolves each parameter independently: the single-provider parameter is served from
the only provider that declares it, while the rest come from the primary. This exercises that selection is
per-parameter, not per-request.

**Decision to resolve in this ticket (HITL):** which specific core parameter is single-provider for the
demo (config-driven `Capability`). See `docs/v1-requirements.md` (Providers, Open / TBD during build)
and `docs/architecture.md` (Arbiter, Capability).

## Acceptance criteria

- [ ] One core parameter is declared by only one provider (recorded here, config-driven).
- [ ] A 6-product-param request returns that parameter from its sole provider and the remaining
      parameters from the primary.
- [ ] Each parameter's provenance reflects its actual origin provider.
- [ ] Unit + mocked-transport integration tests assert per-parameter routing.

## User stories addressed

- User story 6
