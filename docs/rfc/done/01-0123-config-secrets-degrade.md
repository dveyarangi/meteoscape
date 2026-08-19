# Config, secrets, and graceful degradation — implementation plan

**Authored:** 2026-08-19
**Last amended:** 2026-08-19 (final shape: no pre-pass functions — vars ride into `compose`
whole, the binder slices them; catalogue handles; **no `optional`, no degrade** — the public
profile is vendor-neutral and a declared keyed offering without its secret refuses the boot;
TWC-primary is a private deployment's declaration, the embedding edge's first client)

Implements [01-0123](../tickets/01-0123-config-secrets-degrade.md), per its align resolutions of
2026-08-19. Architecture landed first: [ADR-0005](../adr/0005-build-time-composition.md) (2026-08-19
amendment) and [architecture §Config, binders, Weaver](../architecture.md#config-binders-weaver)
(composition-root bullet) state the root-declared profile, the raw operator vars sliced at the
binder, and def-declared degrade this plan implements.

## Boundaries touched

| Boundary | Owner | This plan |
|---|---|---|
| Vendor-config purity | [edge/provider.md](../edge/provider.md) § What every leaf must uphold | **Discharged**: the carve-out for `twc_api_key` / `open_meteo_enabled` ends; `Settings` keeps no vendor-named field. The guard `test_config_imports_nothing_from_nodes` stays. |
| Profile assembly | [ADR-0005](../adr/0005-build-time-composition.md) (amended) | `ProfileConfig` assembled in `main()` from module-level profile data + `Settings` knobs. `compose()`'s `secrets` param becomes `vars` — the raw operator map, whole. **Compatible-in-spirit, breaking-in-spelling** for the de-facto (not promised) embedding path; [edge/embedding.md](../edge/embedding.md) de-facto section updated. |
| Binder strictness | [architecture §Config, binders, Weaver](../architecture.md#config-binders-weaver) | A **required** def binds or raises `CompositionError` (unchanged). The binder now also slices `vars` per impl: secret via `manifest.secret`, same-prefix leftovers as `settings` overrides. `OfferingDef.secret_ref` deleted. |
| Key-absent semantics | ticket resolution; [architecture](../architecture.md#config-binders-weaver) | **Refuse**: a declared keyed offering with an unfilled slot is a `CompositionError`. No degrade mechanism, no `optional` flag, no filtering step. The public profile declares no keyed provider, so keyless runs are the ordinary case. |
| Deployment profiles | [edge/embedding.md](../edge/embedding.md) Roadmap | TWC-primary is a **private deployment's** declaration — the embedding edge's first client, living outside the public shape; parallel-setup-vs-separate-project is [0125](../tickets/01-0125-supported-python-embedding.md)'s align. |
| MCP edge | [edge/mcp.md](../edge/mcp.md) | **No request-path change.** Build-time only. |

## Facts verified in code (2026-08-19)

1. `SourceBinder.build` already holds the manifest when it resolves the secret
   ([composition.py](../../src/meteoscape/nodes/composition.py) — lookup at the top of the loop,
   secret four lines later), so slot-derived lookup deletes the dangling-`secret_ref` failure mode
   rather than adding a check.
2. `ProviderManifest.secret: SecretSlot | None` is singular — one secret per impl is the standing
   type contract, which is what licenses one derived secret name per impl in the var slice.
3. `Settings` uses `env_prefix="METEOSCAPE_"`, `env_file=".env"`, `extra="ignore"`.
   **Falsified during planning (tested 2026-08-19):** pydantic-settings `extra="allow"` does *not*
   collect unknown prefixed vars from the process environment (`model_extra` stays empty), so it
   cannot be the collection mechanism. `Settings` collects the unconsumed vars itself at
   construction — `dotenv_values(env_file)` merged under `os.environ` (environ wins);
   `python-dotenv` is already a pydantic-settings dependency (import verified). A dotenv key with
   no value arrives as `""`, which the empty-string⇒absent rule already covers.
4. TWC's `build` reads `settings.get("cadence_hours", DEFAULT_CADENCE_HOURS)` and validates
   strictly; its key-missing error text names `secret_ref` and must be reworded
   ([twc.py](../../src/meteoscape/nodes/providers/twc.py)).
5. `tests/deterministic/fakes.py` `pinned_settings` relies on init-kwargs-override-env to keep a
   developer's `.env` out of tests. The `vars` collection at `Settings` construction must honor
   the same isolation (`_env_file=None` or injected values — implementation-local);
   `pinned_settings` loses its vendor kwargs (and its TODO).
6. Current consumers of `secret_ref`: `config.py`, `composition.py`, `tests/deterministic/test_config.py`,
   `tests/deterministic/nodes/test_composition.py`, `tests/deterministic/test_server.py`,
   `tests/parity/test_composite.py` (derives it from the manifest already — simplifies to the map).

## Code shapes

### `config.py` — generic residue only

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="METEOSCAPE_", env_file=".env", extra="ignore"   # unchanged
    )
    store_spatial_step: float = 0.0001
    retention_interval: timedelta = timedelta(days=14)

    vars: Mapping[str, str]   # exact spelling implementation-local (attribute or method)
    """The unconsumed METEOSCAPE_* vars — dotenv merged under os.environ (environ wins),
    prefix stripped, names lowercased, values raw strings — collected once at construction
    (fact 3: pydantic does not collect them itself). Settings IS the one world-read: typed
    knobs for the fields it declares, raw access for the per-impl namespace."""
```

No new entity and no separate collection function — `Settings` was always the config entity; it
gains the raw side (resolved 2026-08-19 after several rejected sibling names). Tests isolate the
same way they do today (`_env_file=None` / injected values — implementation-local). Deleted:
`open_meteo_enabled`, `twc_api_key`, `offerings()`, `calculators()`, `profile()`, `secrets()`,
the module TODO. `config.py` also exports `RESERVED_ENV_NAMES` (the declared field names) for the
binder's collision boot-check, and `Settings` gains `root_store() -> StoreSpec` (pure knob
projection). `OfferingDef` loses `secret_ref` and gains **nothing** — an `optional` degrade flag
was considered and thrown away (its only customer was a deployment-specific profile). Its docstring
becomes the **def-author narration** (align resolution: what a profile may declare —
`impl`+`name` select a catalogue spec, `priority` ranks on the shared producer scale, `settings`
overrides are opaque to everyone but `build`, `store` whole-spec-replaces for non-materialized
sources; the secret is the manifest's slot, never the def's, and a profile declaring a keyed
offering commits to supplying its secret). `StoreSpec`, `CalculatorDef`, `ArbiterPolicy`,
`ProfileConfig` are unchanged.

### `composition.py` — mechanism (plain values in, per its own docstring rule)

**No pre-pass functions** (final resolution 2026-08-19, after the earlier reader-function shapes
were rejected as ceremony): the raw `vars` map travels into `compose` whole — its `secrets`
parameter becomes `vars` — and `SourceBinder.build(defs, vars, clock, parameters)` slices it per
def, at the moment of use. The binder already holds the impl and the manifest there; deriving
names anywhere else duplicated its knowledge. The slicing (a private helper in `composition.py`)
is the one home of the env spelling:

- Per impl in the catalogue: prefix = `impl_id` with `-`→`_`, plus `_` (all lowercase, matching
  `vars`). The **secret** is `vars[prefix + slot.name]` when the manifest declares a slot;
  **empty string ⇒ absent** (a blank `.env` line does not enable). Secrets are **never**
  JSON-parsed — a key `"123"` stays a string.
- Every other var under the prefix → a `settings` override keyed by the suffix, value
  `json.loads`-parsed with fallback to the raw string (`"3"`→`3`, `"true"`→`True`, non-JSON →
  string). Type errors surface in `build`'s own validation.
- Boot-checks (`CompositionError`): an impl whose prefix is a prefix of a `RESERVED_ENV_NAMES`
  entry (imported from `config.py`), or of another impl's prefix.
- Vars matching no impl prefix are **ignored** (align resolution; consistent with
  `extra="ignore"`). Residual hazard accepted: a typo in the *impl segment* silently ignores the
  var — `.env.example` is the mitigation. A typo in the *prop segment* lands in overrides and is
  rejected by `build` (stage 3).

`SourceBinder.build` — per def, after the manifest lookup:

```python
secret_value, overrides = _impl_slice(vars, manifest)      # private; names derived, never parsed
if manifest.secret is not None and secret_value is None:
    raise CompositionError(
        f"missing secret for impl {offering.impl!r}: set METEOSCAPE_"
        f"{offering.impl.replace('-', '_').upper()}_{manifest.secret.name.upper()}"
    )
provider = manifest.build(spec, {**offering.settings, **overrides},   # env wins
                          secret_value, clock, parameters)
```

The dangling-`secret_ref` error is deleted, not relocated — the failure it guarded is now
unrepresentable. Key-absent **refuses, always**: a profile declaring a keyed offering commits to
supplying its secret, and the error names the exact env var to set.

### `nodes/providers/builtin.py` / `nodes/calculators/builtin.py` — availability as a system prop

*(Added 2026-08-19: partially discharges [#26](../concerns.md#26-provider--calculator-plugin-scaffolding)
— membership lists off the root.)* Each exports **named handles plus the map**, so profile
authors import one module and never retype an impl name:

```python
# nodes/providers/builtin.py
TWC = TWC_MANIFEST
OPEN_METEO = OPEN_METEO_MANIFEST
CATALOG: ProviderCatalog = {m.impl_id: m for m in (TWC, OPEN_METEO)}
```

The builtin modules import the concrete plugin modules; `catalog/` stays faces-only. The five
test modules importing catalogues from `meteoscape.server` re-import from these homes (`compose`
stays a `server` import — that *is* the edge's function).

### `server.py` — the MCP product's profile, declared

```python
from .nodes.providers import builtin as providers
from .nodes.calculators import builtin as calculators

PROVIDER_CATALOG = providers.CATALOG                      # availability: system's
CALCULATOR_CATALOG = calculators.CATALOG

# The public server's profile — vendor-neutral, keyless; no global default exists (ADR-0005).
# TWC-primary is a private deployment's declaration, composed at its own root (embedding edge).
OFFERINGS: tuple[OfferingDef, ...] = (                    # enablement: this edge's
    OfferingDef(impl=providers.OPEN_METEO.impl_id, priority=0),
)
CALCULATORS: tuple[CalculatorDef, ...] = (  # moved verbatim from Settings.calculators()
    CalculatorDef(outputs=..., inputs=..., fn_id="wind_uv", priority=0),
)


def main() -> None:
    settings = Settings()                    # the one world-read: knobs + vars
    gateway = compose(
        ProfileConfig(OFFERINGS, CALCULATORS, settings.root_store(), ArbiterPolicy()),
        PROVIDER_CATALOG, CALCULATOR_CATALOG, settings.vars, Metronome(),
    )
```

Every input provided exactly once; no pre-pass, no branches. `compose()`'s only change is the
`secrets` parameter becoming `vars`.

### `twc.py` and `open_meteo.py` — plugin-side

- `SecretSlot("twc_api_key")` → `SecretSlot("api_key")` (impl-local name; derived env spelling
  `METEOSCAPE_TWC_API_KEY` is character-identical to today's, so the operator `.env` keeps
  working).
- Key-missing error reworded to name the derived var: `"twc requires an API key; set
  METEOSCAPE_TWC_API_KEY"` (vendor module naming its own env var is plugin-side vocabulary —
  legal).
- `build` rejects unknown `settings` keys (`CompositionError` listing them) — the typo guard.

## Key-absent flow (the ticket's headline behavior, re-cut 2026-08-19)

The public server declares Open-Meteo alone, so it boots keyless — the ordinary case, not a
degraded one. A profile that declares TWC (an embedder-shaped test today; the private
deployment's root when the embedding edge stands up) and lacks `METEOSCAPE_TWC_API_KEY` →
`CompositionError` naming that exact var; with the key present, TWC binds primary by its declared
`priority` and a live fault at
request time falls through to Open-Meteo per [0121](../tickets/done/01-0121-second-provider-fallback.md).
TWC-primary composition is **proven but not shipped**: `test_server.py` composes it from a test
profile + test vars, and the opt-in parity composite runs it live. No vendor branch exists
anywhere on this path — TWC appears only as data in profile declarations and the catalogue.

## Stages

**Stage 1 — mechanism, additive (green throughout).** The private var-slicer (`_impl_slice` or
equivalent) + boot-checks in `composition.py`, and the two `builtin.py` catalogue modules
(handles + `CATALOG`) — all additive, with
deterministic tests (secret picked by derived name; empty-string secret absent; secrets never
JSON-parsed; override scalar parsing incl. non-JSON fallback; reserved-prefix and nested-prefix
boot-checks). Nothing wired; binder untouched.

**Stage 2 — the swap (red inside the stage, green at its end; too many seams to shim
individually).** Binder consumes `vars` per def (slice → refuse on unfilled slot → env-wins merge
into `build`'s settings); `compose`'s `secrets` param becomes `vars`; the public `OFFERINGS`
drops to Open-Meteo alone (TWC-primary lives in test profiles and, later, the private
deployment's root);
`OfferingDef.secret_ref` deleted; `config.py` slimmed (fields, methods, TODO out; `Settings`
gains `vars` and `root_store()`, exports `RESERVED_ENV_NAMES`; `extra="ignore"` stays);
`server.py`'s hand-assembled maps replaced by builtin imports (test modules re-point their
catalogue imports) and `main()` becomes the single-`compose` shape; TWC slot renamed `api_key` +
error reword. Test rework in the same stage: `fakes.pinned_settings` loses vendor kwargs (fact 5;
its TODO dies), `test_config.py` (`Settings.vars` — env-wins merge, prefix strip, field
exclusion, isolation from the real `.env`; knobs; purity guard stays), `test_composition.py` (two
`secret_ref` tests become: secret-reaches-build via slice, missing-slot-secret-refuses naming the
env var, unknown-impl-still-refuses), `test_server.py` (defs without `secret_ref`; the public
profile boots keyless on Open-Meteo through the real `main()` path; an **embedder-shaped test
profile** with TWC + test vars composes TWC as primary; the same profile without the key
refuses),
`tests/parity/test_composite.py` (drops ref derivation, supplies vars — opt-in live suite,
verified by run where a key is available).

**Stage 3 — strictness and narration (green to green).** TWC `build` unknown-key rejection +
test; `OfferingDef` def-author docstring; `.env.example` (tracked; the operator narration: the
knobs, `METEOSCAPE_TWC_API_KEY=`, and one comment stating the `METEOSCAPE_<IMPL>_<PROP>`
derivation); [edge/provider.md](../edge/provider.md) carve-out sentence replaced by the discharged
form; delivery-status rows (0123 → Done; "Configured keyed-provider startup" behavior text) at
close.

Acceptance criteria ↔ proof: criterion 1 (re-cut) — stage 2's `test_config.py` +
`server.py` shape; criterion 2 — stage 1 slice tests + stage 2 binder test; criterion 3 (re-cut)
— stage 2's keyless-public-boot, refusal-naming-the-var, and embedder-shaped TWC-primary tests;
criterion 4 — stage 2 `test_server.py`; criterion 5 — stage 2 both startup tests; criterion 6 —
purity guard green with the fields gone, edge record discharge in stage 3.

## Out of scope / follow-ups

- **v1-requirements story 11** promises "enable/disable providers and set priority via typed
  config"; the align supersedes it (enable = profile membership at a root; priority = profile data;
  no env-side enable/disable). Story 13's "missing optional secret degrades gracefully" is
  likewise superseded — no degrade mechanism exists. The requirements doc is already flagged as
  awaiting replacement
  ([delivery status](../tickets/README.md)); no edit here — the ticket's resolutions are the
  fresher authority.
- Profile-as-config-file, plugin discovery, optional sets and symmetric set selection —
  [#26](../concerns.md#26-provider--calculator-plugin-scaffolding) / [0125](../tickets/01-0125-supported-python-embedding.md).
  The *first* named shipped set (`builtin`) lands here; everything beyond it stays #26's.
- Storeless producers and self-homogenization — [#37](../concerns.md#37-storeless-materialized-producers-and-read-back-homogenization)
  (widened this align); nothing here moves the binder's store rules.
- The ledger rides this injection path next ([0124](../tickets/01-0124-vendor-call-ledger.md));
  the Mongo connection string is the second slot consumer ([0130](../tickets/01-0130-mongo-obs-source.md)).
- No migration: the operator-visible env spelling is unchanged (`METEOSCAPE_TWC_API_KEY`); the
  dropped `METEOSCAPE_OPEN_METEO_ENABLED` had no non-default user.
