# Config and secrets — implementation plan

**Authored:** 2026-08-19
**Last amended:** 2026-08-19, seventh re-cut (review): **the namespace sweep is gone too.**
`Settings` no longer collects unconsumed vars; secrets are read by *derived name*
(`secrets_from_env(secret_slots(catalog))` — config owns the spelling, the catalogue answers which
slots exist), and `compose`/`SourceBinder.build` take an **`impl_id` → value secrets map** an
embedder can supply from a vault with no env spelling at all. The sweep was residue of the
override channel: it existed to feed the scanner. Sixth re-cut: **the env `settings`-override
channel is cut.** Env carries secrets and the typed scalars; structured per-offering configuration is
declared on the `OfferingDef` at a composition root (a config file may fill it later, 0125). This
deletes the prefix scanning, JSON value parsing, override merge, prefix boot-checks, and the
`RESERVED_ENV_NAMES` export — a config-file parser that had grown inside the env namespace with
no customer. Previous: fifth re-cut (review): **a def selects and ranks, never restating
a manifest's declarations** — `CalculatorManifest` gains the co-produced `outputs`/`inputs`
(kernel facts, mirroring `OfferingSpec`), `CalculatorDef` slims to selection + policy; both def
kinds select via id-constant handles exported by the builtin modules (defs stay plain strings —
a protocol/coercion variant was rejected as ceremony) and default `priority=0`, guarded by a
the reconciler's bind-order contract (a weave-time tie refusal was built and removed as
contradicting it). Landed in
architecture §Config bullet, ADR-0005 amendment, glossary `CalculatorDef`, ticket note.
Previous: fourth validation pass. Counterexamples against the third pass's
"grep-closed" inventory: `_compose_both` is a TWC-primary e2e path (must not fold into
`server.OFFERINGS`); `SourceBinder.build(..., secrets=)` keyword sites live in `test_arbiter.py`
and `test_weaver.py` as well as `test_composition.py`; the composite keys both its vars map and its
`--twc-api-key` option off `SecretSlot.name`, which the slot rename to `api_key` breaks;
`main()` ends in `app.run()` so tests must assemble as `main()` does, not invoke it. Earlier
passes: consumer inventory of the dying `Settings` surface; stale degrade wording purged; `vars`
pinned as a non-field; boot-check scope pinned to the declared set; parity keyword-callers and
e2e `profile()` calls added to stage 2.

Implements [01-0123](../../tickets/done/01-0123-config-secrets-degrade.md), per its align resolutions of
2026-08-19. Architecture landed first: [ADR-0005](../../adr/0005-build-time-composition.md) (2026-08-19
amendment) and [architecture §Config, binders, Weaver](../../architecture.md#config-binders-weaver)
(composition-root bullet) state the root-declared profile, the impl-keyed secrets map read by
derived name, and refuse-on-unfilled-slot semantics this plan implements. **No `optional`, no
degrade** — the public profile is vendor-neutral; TWC-primary is a private deployment's
declaration ([pilot requirements](../../pilot-requirements.md)), the embedding edge's first client.

## Boundaries touched

| Boundary | Owner | This plan |
|---|---|---|
| Vendor-config purity | [edge/provider.md](../../edge/provider.md) § What every leaf must uphold | **Discharged**: the carve-out for `twc_api_key` / `open_meteo_enabled` ends; `Settings` keeps no vendor-named field. The guard `test_config_imports_nothing_from_nodes` stays; a field-name guard (stage 3) proves no builtin-impl id is embedded in a `Settings` field. |
| Profile assembly | [ADR-0005](../../adr/0005-build-time-composition.md) (amended) | `ProfileConfig` assembled in `main()` from module-level profile data + `Settings` knobs. `compose()` keeps a `secrets` param, now keyed by `impl_id` (was `secret_ref` names) and fillable without env. **Compatible-in-spirit, breaking-in-spelling** for the de-facto (not promised) embedding path; [edge/embedding.md](../../edge/embedding.md) de-facto section already updated. |
| Binder strictness | [architecture §Config, binders, Weaver](../../architecture.md#config-binders-weaver) | A **required** def binds or raises `CompositionError` (unchanged). The binder takes an `impl_id`-keyed **secrets map** and owns only the policy — an unfilled declared slot refuses. Deriving env names is config's (`secrets_from_env`); `OfferingDef.secret_ref` deleted; no env `settings` channel. |
| Key-absent semantics | ticket resolution; [architecture](../../architecture.md#config-binders-weaver) | **Refuse**: a declared keyed offering with an unfilled slot is a `CompositionError` naming the impl, the slot, and the derived env var (ticket criterion 3). No degrade mechanism, no `optional` flag, no filtering step. The public profile declares no keyed provider, so keyless runs are the ordinary case. |
| Deployment profiles | [pilot requirements](../../pilot-requirements.md); [edge/embedding.md](../../edge/embedding.md) Roadmap | TWC-primary is the **pilot deployment's** declaration — the embedding edge's first client, living outside the public shape; parallel-setup-vs-separate-project is [0125](../../tickets/01-0125-supported-python-embedding.md)'s align, and the bee-line rides the Open-Meteo path until the correction workstream (sequencing recorded in the pilot requirements). |
| MCP edge | [edge/mcp.md](../../edge/mcp.md) | **No request-path change.** Build-time only. |
| SecretSlot meaning | [edge/provider.md](../../edge/provider.md) (still teaches optionality) | A `SecretSlot` is a **name**, not an optionality declaration. Stage 3 rewrites that paragraph to match architecture's refuse rule; [#35](../../concerns.md#35-calculator-satisfiability-vs-optional-provider-degrade) keeps the future optional-plugin collision, vacated at boot. |

## Facts verified in code (2026-08-19)

1. `SourceBinder.build` already holds the manifest when it resolves the secret
   ([composition.py](../../../src/meteoscape/nodes/composition.py) — lookup at the top of the loop,
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
   ([twc.py](../../../src/meteoscape/nodes/providers/twc.py)).
   `test_build_requires_a_secret` matches `"API key"` — the reworded text still contains that
   phrase, so the test stays as a verify, not a rewrite.
5. `tests/deterministic/fakes.py` `pinned_settings` relies on init-kwargs-override-env to keep a
   developer's `.env` out of tests. The `vars` collection at `Settings` construction must honor
   the same isolation (`_env_file=None` or injected values — implementation-local);
   `pinned_settings` loses its vendor kwargs (and its TODO). *(Sixth re-cut: with no env
   `settings` channel, every var that is not a declared impl's secret name is inert, so a
   developer's real `.env` cannot fail the suite — isolation stays good hygiene, not a
   correctness requirement.)*
6. Current consumers of `secret_ref`: `config.py`, `composition.py`, `tests/deterministic/test_config.py`,
   `tests/deterministic/nodes/test_composition.py`, `tests/deterministic/test_server.py`,
   `tests/parity/test_composite.py` (derives it from the manifest already — simplifies to the map).
   **Corrected on the second validation pass:** the other two parity modules also consume the
   dying surface — `test_twc.py` constructs `Settings(open_meteo_enabled=..., twc_api_key=...)`
   and both `test_twc.py` and `test_open_meteo.py` call `compose(..., secrets=settings.secrets())`
   with `secrets=` as a **keyword**, which the param rename breaks (positional callers are
   unaffected). All three parity modules are stage-2 rework. One compatibility gift: the derived
   var-map key for TWC's secret is `twc_api_key` (impl prefix + impl-local slot name) — character-
   identical to today's slot-keyed map key — so existing `{"twc_api_key": key}` dicts stay valid;
   only the `Settings` kwargs and keyword param spelling change. **The gift is TWC-specific:**
   `test_composition.py`'s fake uses `SecretSlot("api_key")` and `secrets={"api_key": ...}` —
   after the slice that map key becomes `fake_api_key`.
7. **`test_e2e_forecast.py` has two composers, not one `profile()` call-site.**
   `_compose_default` is the shipped (today: keyless-OM) path and takes an optional
   `store_spatial_step` knob override. `_compose_both` composes TWC-primary + Open-Meteo and is
   the body of three tests (TWC horizon, past-TWC capability-mismatch, primary-429 fall-through).
   Folding both onto `server.OFFERINGS` would drop TWC from those three tests.
8. **`SourceBinder.build(..., secrets=)` keyword sites** (the binder param rename, same break as
   `compose`): `test_composition.py` (many, including empty `{}`), `test_arbiter.py` `_bind`,
   `test_weaver.py` `_profile`. `tests/deterministic/test_parity_comparison.py`'s `secrets=` is
   `format_summary`'s scrub argument — a different function, untouched.
9. **Composite parity derives two things from `SecretSlot.name`:** the `secret_ref` (deleted) and
   the pytest option `--{slot.replace('_', '-')}` plus the secrets-dict key. Today the slot is
   `twc_api_key`, so the option is `--twc-api-key` ([conftest.py](../../../tests/parity/conftest.py))
   and the dict key is `twc_api_key`. After the slot goes impl-local (`api_key`) that derivation
   would look up `--api-key` (does not exist) and supply `{"api_key": ...}` (the binder looks up
   `twc_api_key`). `--twc-api-key` and the env fallback `METEOSCAPE_TWC_API_KEY` stay; the
   composite builds a vars dict keyed by the **derived** name, not the slot name.
10. `main()` ([server.py](../../../src/meteoscape/server.py)) ends in `build_mcp_app(...).run()`.
    Tests that "go through the real `main()` path" assemble as `main()` does (`Settings` +
    declared profile data + `compose`); they do not call `main()` (it hangs on the server loop).
11. Open-Meteo's `build` does `del settings, secret_value` — a *declared* settings key would
    vanish silently until stage 3's unknown-key rejection. TWC already type-checks
    `cadence_hours` but does not reject unknown keys. *(Sixth re-cut: env can no longer inject
    settings, so this guard now protects code-declared maps only.)*

## Code shapes

### `config.py` — generic residue only

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="METEOSCAPE_", env_file=".env", extra="ignore"   # unchanged
    )
    store_spatial_step: float = 0.0001
    retention_interval: timedelta = timedelta(days=14)

    # The unconsumed METEOSCAPE_* vars — dotenv merged under os.environ (environ wins),
    # prefix matched case-insensitively (parity with pydantic's env matching), stripped,
    # names lowercased, values raw strings — collected once at construction
    # (fact 3: pydantic does not collect them itself). MUST NOT be a declared pydantic field:
    # a field named `vars` would itself consume METEOSCAPE_VARS and join the reserved names.
    # Property / method / private attr, and the exact identifier, are implementation-local
    # (`vars` shadows a builtin; something like `env_vars` is equally acceptable).
    @property
    def vars(self) -> Mapping[str, str]: ...
```

`Settings` IS the one world-read: typed knobs for the fields it declares, raw access for the
per-impl namespace.

```python
# config.py — defs are selection + policy, nothing restated (2026-08-19 re-cut)
@dataclass(frozen=True)
class OfferingDef:
    impl: str            # an id — profiles pass the builtin module's id constant
    priority: int = 0
    name: str | None = None
    settings: Mapping[str, object] = field(default_factory=dict)
    store: StoreSpec | None = None

@dataclass(frozen=True)
class CalculatorDef:
    fn_id: str           # likewise
    priority: int = 0
    name: str | None = None
    stored: bool = False
```

`CalculatorDef` **loses `outputs` and `inputs`** — they are the kernel's own facts and move to
`CalculatorManifest` (below), exactly as `OfferingSpec` carries the provider's product row. A
def-side group also implied subsettable co-production, which ADR-0004's atomic group forbids —
the move makes that misdeclaration unrepresentable. The `priority` default is made safe by the
reconciler's own contract (below). **No protocols, no coercion** (rejected as ceremony): the short
spelling comes entirely from the builtin modules exporting each **id as a named constant**, so
`OfferingDef(providers.TWC)` passes a plain string.

No new entity and no separate collection function — `Settings` was always the config entity; it
gains the raw side (resolved 2026-08-19 after several rejected sibling names). Tests isolate the
same way they do today (`_env_file=None` / injected values — implementation-local). Deleted:
`open_meteo_enabled`, `twc_api_key`, `offerings()`, `calculators()`, `profile()`, `secrets()`,
the module TODO. The consumed-field names stay **private** to `config.py` (they only mark which
vars the typed fields already took), and `Settings` gains `root_store() -> StoreSpec` (pure knob
projection). `OfferingDef` loses `secret_ref` and gains **nothing** — an `optional` degrade flag
was considered and thrown away (its only customer was a deployment-specific profile). Its docstring
becomes the **def-author narration** (align resolution: what a profile may declare —
`impl`+`name` select a catalogue spec, `priority` ranks on the shared producer scale, `settings`
overrides are opaque to everyone but `build`, `store` whole-spec-replaces for non-materialized
sources; the secret is the manifest's slot, never the def's, and a profile declaring a keyed
offering commits to supplying its secret; the narration states the one rule for both def kinds:
*a def selects and ranks; it never restates what the plugin declares*). `StoreSpec`,
`ArbiterPolicy`, `ProfileConfig` are unchanged; `CalculatorDef` slims per the block above.

### `composition.py` — mechanism (plain values in, per its own docstring rule)

**No pre-pass functions** (final resolution 2026-08-19, after the earlier reader-function shapes
were rejected as ceremony): the raw `vars` map travels into `compose` whole — its `secrets`
parameter becomes the raw map (name implementation-local) — and
`SourceBinder.build(defs, vars, clock, parameters)` slices it per def, at the moment of use.
The binder already holds the impl and the manifest there; deriving names anywhere else duplicated
its knowledge. The slicing (a private helper in `composition.py`; tests prove the behaviors,
not the helper's name) is the one home of the env spelling:

- The **secret** only. Its var name is derived from the impl id (hyphens → underscores,
  lowercased, matching the collected `vars`) plus the manifest's `SecretSlot` name — a lookup,
  never a scan, so there is no suffix grammar to mis-parse. **Empty string ⇒ absent** (a blank
  `.env` line does not enable), and secrets are **never** parsed — a key `"123"` stays a string.
- **No `settings` channel in env** (re-cut 2026-08-19, final). Structured per-offering
  configuration is declared on the `OfferingDef` at a composition root; env carries secrets and
  the typed scalars, as env is for. What this deletes: same-prefix scanning, `json.loads` value
  parsing, the override merge, the reserved-name and nested-prefix boot-checks, and
  `RESERVED_ENV_NAMES`' export — a config-file parser that had grown inside the env namespace,
  serving no customer (the pilot root, the only tuner, writes `settings={...}` in code). A config
  file may fill the same field later ([0125](../../tickets/01-0125-supported-python-embedding.md)).
- Any var that is not a declared impl's secret name is **inert** — including a leftover
  `METEOSCAPE_TWC_API_KEY` under the vendor-neutral public profile, and any stale
  `METEOSCAPE_OPEN_METEO_ENABLED`. With no scanning there is nothing to mis-slice and no prefix
  to guard; `.env.example` documents the surviving vocabulary. `build` still rejects unknown keys
  in the **declared** `settings` map (typo guard, stage 3).

`SourceBinder.build` — per def, after the manifest lookup:

```python
secret_value = secret_for(vars, manifest)         # derived name lookup; empty ⇒ absent
if manifest.secret is not None and secret_value is None:
    raise CompositionError(
        f"missing secret {manifest.secret.name!r} for impl {offering.impl!r}: "
        f"set {secret_env_name(offering.impl, manifest.secret.name)}"
    )
provider = manifest.build(spec, offering.settings,   # as declared; env adds nothing
                          secret_value, clock, parameters)
```

The dangling-`secret_ref` error is deleted, not relocated — the failure it guarded is now
unrepresentable. Key-absent **refuses, always**: a profile declaring a keyed offering commits to
supplying its secret, and the error names the impl, the slot, and the exact env var to set
(ticket criterion 3).

**`CalculatorManifest` gains the product row; `CalculatorBinder` reads it** (fifth re-cut):

```python
@dataclass(frozen=True)
class CalculatorManifest:
    fn_id: str
    fn: CombineFn
    outputs: frozenset[ParameterId]   # the co-produced group — the kernel's own fact
    inputs: frozenset[ParameterId]
```

`CalculatorBinder.build` takes `outputs`/`inputs` from the manifest instead of the recipe,
still resolving output `ParameterDef`s against the `ParameterTable` (unknown-output refusal
unchanged). Every construction gains the declaration: [wind.py](../../../src/meteoscape/nodes/calculators/wind.py)
(the real group) and the twelve fake manifests (`test_composition.py` ×9, `test_weaver.py` ×3 —
grep-closed).

**What makes `priority=0` a safe default — the reconciler's standing contract, not a new
guard:** `PriorityReconciler`'s docstring predates this ticket: *"Lower priority wins; equal
priority keeps candidate (bind) order — stable sort"* ([arbiter.py](../../../src/meteoscape/nodes/arbiter.py)).
Ties are deterministic and *specified* — the ordered profile declaration is the tie-break. A
weave-time `refuse_priority_ties` precondition was implemented and then **removed** (2026-08-19):
it turned that documented behavior into a boot error, contradicting the contract it claimed to
protect. No tie mechanism exists; none is needed.

### `nodes/providers/builtin.py` / `nodes/calculators/builtin.py` — availability as a system prop

*(Added 2026-08-19: partially discharges [#26](../../concerns.md#26-provider--calculator-plugin-scaffolding)
— membership lists off the root.)* Each exports **named handles plus the map**, so profile
authors import one module and never retype an impl name:

```python
# nodes/providers/builtin.py
TWC = twc.IMPL_ID                       # "twc" — the handle IS the id, a plain string
OPEN_METEO = open_meteo.IMPL_ID
CATALOG: ProviderCatalog = {TWC: TWC_MANIFEST, OPEN_METEO: OPEN_METEO_MANIFEST}
```

The builtin modules import the concrete plugin modules; `catalog/` stays faces-only. The five
test modules importing catalogues from `meteoscape.server` re-import from these homes (`compose`
stays a `server` import — that *is* the edge's function). `main()` passes `providers.CATALOG` /
`calculators.CATALOG` directly; it does **not** re-export them under the old `PROVIDER_CATALOG`
names — after the five tests re-point, that alias has no remaining in-tree customer, and keeping
it would leave availability reachable through the edge.

### `server.py` — the MCP product's profile, declared

```python
from .nodes.providers import builtin as providers
from .nodes.calculators import builtin as calculators

# The public server's profile — vendor-neutral, keyless; no global default exists (ADR-0005).
# TWC-primary is a private deployment's declaration, composed at its own root (embedding edge).
OFFERINGS: tuple[OfferingDef, ...] = (OfferingDef(providers.OPEN_METEO),)     # selection only
CALCULATORS: tuple[CalculatorDef, ...] = (CalculatorDef(calculators.WIND_UV),)


def main() -> None:
    init_observability()                     # unchanged, as is build_mcp_app(...).run() below
    settings = Settings()                    # the one world-read: knobs + vars
    clock = Metronome()
    gateway = compose(
        ProfileConfig(OFFERINGS, CALCULATORS, settings.root_store(), ArbiterPolicy()),
        providers.CATALOG, calculators.CATALOG, settings.vars, clock,
    )
    build_mcp_app(gateway, clock).run()
```

Every input provided exactly once; no pre-pass, no branches. `compose()`'s only change is the
`secrets` parameter becoming the raw vars map (parameter name implementation-local; avoid
shadowing the `vars` builtin in signatures). The same rename applies to `SourceBinder.build`.

### `twc.py` and `open_meteo.py` — plugin-side

- `SecretSlot("twc_api_key")` → `SecretSlot("api_key")` (impl-local name; derived env spelling
  `METEOSCAPE_TWC_API_KEY` is character-identical to today's, so the operator `.env` keeps
  working).
- Key-missing error reworded to name the derived var: `"twc requires an API key; set
  METEOSCAPE_TWC_API_KEY"` (vendor module naming its own env var is plugin-side vocabulary —
  legal). Binder already refuses first; this remains the direct-`build` guard
  (`test_build_requires_a_secret`).
- `build` rejects unknown `settings` keys (`CompositionError` listing them) — the typo guard.

## Key-absent flow (the ticket's headline behavior, re-cut 2026-08-19)

The public server declares Open-Meteo alone, so it boots keyless — the ordinary case, not a
degraded one. A profile that declares TWC (an embedder-shaped test today; the private
deployment's root when the embedding edge stands up) and lacks `METEOSCAPE_TWC_API_KEY` →
`CompositionError` naming the impl, the slot, and that exact var; with the key present, TWC binds
primary by its declared `priority` and a live fault at
request time falls through to Open-Meteo per [0121](../../tickets/done/01-0121-second-provider-fallback.md).
TWC-primary composition is **proven but not shipped**: `test_server.py` composes it from a test
profile + test vars, and the opt-in parity composite runs it live. No vendor branch exists
anywhere on this path — TWC appears only as data in profile declarations and the catalogue.

## Stages

**Stage 1 — mechanism, additive (green throughout).** The private var-slicer (`_impl_slice` or
equivalent) + boot-checks in `composition.py`, the two `builtin.py` catalogue modules
(handles + `CATALOG`), **`CalculatorManifest.outputs`/`inputs` with every construction updated**
(the binder still reads the def's copy this stage, so green), the id-constant handles on the
builtin modules + `priority=0` defaults on both def kinds (defaults are compatible additions), and the
— all additive, with
deterministic tests proving **behaviors** (secret picked by derived name `prefix+slot`; empty-string
secret absent; secret stays a raw string; hyphenated impl id derives an underscore name; a
slotless impl takes no secret; another impl's var is ignored; `secret_env_name` spelling;
). Nothing
wired; binder untouched. Helper names are not a test API.

**Stage 2 — the swap (red inside the stage, green at its end; too many seams to shim
individually).** Binder consumes `vars` per def (slice → refuse on unfilled slot → env-wins merge
into `build`'s settings); `compose`'s and `SourceBinder.build`'s `secrets` param become the raw
map; the public `OFFERINGS` drops to Open-Meteo alone (TWC-primary lives in test profiles and,
later, the private deployment's root);
`OfferingDef.secret_ref` deleted; **`CalculatorDef.outputs`/`inputs` deleted and
`CalculatorBinder` switched to the manifest's row**; `config.py` slimmed (fields, methods, TODO out; `Settings`
gains `vars` and `root_store()`, keeps the consumed-name set private; `extra="ignore"` stays);
`server.py`'s hand-assembled maps replaced by builtin imports (test modules re-point their
catalogue imports; `main()` does not re-export the maps) and `main()` becomes the single-`compose`
shape with handle-and-default defs; TWC slot renamed `api_key` + error reword. Test rework in the
same stage (`CalculatorDef` construction sites are grep-closed: `server.py`, `test_config.py`,
`test_server.py`, `test_composition.py` ×6, `test_composite.py` — each drops its
`outputs`/`inputs`):

- `fakes.pinned_settings` loses vendor kwargs (fact 5; its TODO dies). Isolation of `.env` stays
  — required, not optional, because a leftover `OPEN_METEO_ENABLED` fails the suite after stage 3.
- `test_config.py` — enablement-projection tests (`offerings()` / `secrets()` / disabled-OM /
  TWC-adds-primary) **deleted with no Settings-side replacement** (enablement is profile data,
  proven in `test_server.py`). New: `Settings.vars` — env-wins merge, prefix strip, field
  exclusion, isolation from the real `.env`; knobs; purity guard stays.
- `test_composition.py` — two `secret_ref` tests become: secret-reaches-build via slice with
  vars keyed `fake_api_key` (not `api_key`), missing-slot-secret-refuses naming impl + slot +
  env var, unknown-impl-still-refuses. Every `secrets=` keyword on `SourceBinder.build` is
  renamed (empty `{}` stays valid).
- `test_arbiter.py` `_bind` and `test_weaver.py` `_profile` — same keyword rename (empty `{}`).
- `test_server.py` — defs without `secret_ref`; the public profile boots keyless on Open-Meteo
  by assembling as `main()` does (`OFFERINGS` + `CALCULATORS` + `Settings` knobs + `compose`),
  not by calling `main()`; an **embedder-shaped test profile** with TWC + test vars composes TWC
  as primary; the same profile without the key refuses.
- `test_e2e_forecast.py` — `_compose_default` assembles `ProfileConfig` from `server.OFFERINGS` /
  `server.CALCULATORS` and `settings.root_store()` (keep the `store_spatial_step=` knob override;
  do not go through the deleted `profile()`). `_compose_both` becomes the same embedder-shaped
  TWC-primary profile + `{twc_api_key: "test-key"}` as `test_server.py` — it does **not** fold
  onto `server.OFFERINGS` (fact 7).
- `tests/parity/test_composite.py` — drops `secret_ref`; supplies a vars dict keyed by the
  **derived** name (`twc_api_key`, not the new slot `api_key`); `--twc-api-key` stays as the
  pytest option (do not re-derive it from `SecretSlot.name`); env fallback
  `METEOSCAPE_TWC_API_KEY` stays (today's skip text).
- `tests/parity/test_twc.py` and `tests/parity/test_open_meteo.py` — replace `Settings` vendor
  kwargs with directly-constructed defs + a vars dict; key sources for TWC remain
  `--twc-api-key` then `METEOSCAPE_TWC_API_KEY`; fix the keyword `secrets=` call sites.
  OM-only composes the shipped `OFFERINGS` (developer TWC key in vars is then inert).

The parity trio is an opt-in live suite outside the CI gate — stage 2's "green" covers their
**collection and construction** (import-time and def-building correctness via the deterministic
suite); their live verification happens on the next keyed run.

**Stage 3 — strictness and narration (green to green).** Unknown-`settings`-key rejection in
**both** builds + tests — TWC's, and Open-Meteo's (without it, a stale
`METEOSCAPE_OPEN_METEO_ENABLED` in an operator's `.env` would land in OM's overrides as
`{"enabled": true}` and vanish silently — the exact stale-var case the typo guard exists for;
with it, the leftover fails the boot naming the key, which the migration bullet below accepts);
`OfferingDef` def-author docstring; `SecretSlot` docstring (a name, not a secrets-map key);
a **vendor-named-field regression guard** (criterion 6's existing proof — the import guard —
checks imports, not field names; a deterministic test asserts no `Settings` field name embeds a
builtin-catalogue impl id, and the discharged edge-record sentence names *it* as validator, not
the import guard alone);
`.env.example` (tracked; the operator narration: the knobs, `METEOSCAPE_TWC_API_KEY=`, and one
comment stating the `METEOSCAPE_<IMPL>_<PROP>` derivation).

Close-out docs — the sentences that would otherwise still teach the old shape, all in this
stage so the tree matches the code:

- [edge/provider.md](../../edge/provider.md): carve-out sentence replaced by the discharged form
  naming the field-name guard; the **SecretSlot-as-optionality** paragraph (absent value →
  offering never enabled, graceful degrade is `Settings`' policy, dangling-ref validators,
  `SecretSlot("twc_api_key")`) rewritten to: a slot is a name; an unfilled slot of a *declared*
  offering refuses the boot; validators are the new slice/refusal tests; TWC's slot is `api_key`.
- [ADR-0005](../../adr/0005-build-time-composition.md) mermaid still lists `secret_ref` on
  `OfferingDef` — drop it. Prose already states the 2026-08-19 amendment.
- [architecture.md](../../architecture.md) catalogues bullet still says "secrets are an injected
  map"; composition-root `compose(..., secrets, ...)` spelling — both become the raw operator
  vars. Reach's "graceful degrade" (a parameter no enabled producer serves is absent) is a
  **different** degrade and stays.
- [module-layout.md](../../module-layout.md): injection signatures `secrets` → the raw map;
  `config.py` line drops `secrets()`. (`builtin.py` is already drawn — destination, not a new
  invention here.)
- [#35](../../concerns.md#35-calculator-satisfiability-vs-optional-provider-degrade): one sentence
  that boot-degrade is gone, so the collision waits on a future optional-plugin story (#26);
  the concern stays open. [#39](../../concerns.md#39-python-embedding-surface-and-public-failures)
  "secrets map" → raw operator vars (de-facto `compose` inputs).
- Delivery-status rows (0123 → Done; "Configured keyed-provider startup" behavior text) at
  close.

**Implementation state (2026-08-19):** all three stages are **implemented and green** — 426
deterministic tests, ruff, format, and pyright clean — in the final shape: `operator_vars` on
`Settings` (consumed names private), `secret_for` + `secret_env_name` as the binder's only env
reading, builtin catalogue modules with id-constant handles, vendor-neutral `OFFERINGS`,
`CalculatorManifest` carrying the I/O row with `CalculatorDef` slimmed, `priority` defaults,
slot `api_key`, both `build`s' unknown-key gate over code-declared settings, and `.env.example`.
Built and then **removed** during review: the `optional` degrade flag, the config `Protocol`s
and coercion, the weave-time tie refusal, and the env `settings`-override channel with its
prefix grammar and guards. Remaining: `/review-impl` and the close-out doc discharges below.

Acceptance criteria ↔ proof: criterion 1 (re-cut) — stage 2's `test_config.py` +
`server.py` shape; criterion 2 — stage 1 slice tests + stage 2 binder test; criterion 3 (re-cut)
— stage 2's keyless-public-boot, refusal naming impl + slot + env var, and embedder-shaped
TWC-primary tests; criterion 4 — stage 2 `test_server.py`; criterion 5 — stage 2 both startup
tests plus e2e `_compose_both` still proving TWC-primary at request time; criterion 6 — the
stage-3 vendor-named-field regression guard (the import guard alone proves imports, not
fields), plus the edge-record discharge naming it.

## Impact

**Must change.** `Settings` surface and every call site listed in facts 6–9; public profile
drops TWC; binder secret lookup; TWC slot name; both `build`s' unknown-key gate; builtin
catalogue modules; `CalculatorManifest` (+13 construction sites) and `CalculatorDef` (+its
construction sites) per the fifth re-cut, with `CalculatorBinder`;
the neighbor sentences listed in stage 3 (edge record, ADR mermaid,
architecture spelling, module-layout signatures, #35/#39 wording).

**Must verify.** Isolation of `Settings.vars` from a real `.env`; leftover
`METEOSCAPE_OPEN_METEO_ENABLED` fails post-stage-3; leftover `METEOSCAPE_TWC_API_KEY` is inert
on the public profile; composite still finds `--twc-api-key`; e2e TWC-horizon / 429 tests still
compose two producers; `test_build_requires_a_secret` still matches.

**May simplify.** `server.py` dropping the catalogue aliases; `pinned_settings` shrinking to an
isolation helper (or disappearing if tests construct `Settings` with `_env_file=None` directly).

**Leave alone.** Request path, MCP contract, fall-through, store rules, `SecretSlot` remaining
singular, parity CLI option spelling, operator-visible `METEOSCAPE_TWC_API_KEY`. Reach's
parameter-absent "graceful degrade" (a different meaning). Scrub `secrets=` on `format_summary`.

## Out of scope / follow-ups

- **v1-requirements story 11** promises "enable/disable providers and set priority via typed
  config"; the align supersedes it (enable = profile membership at a root; priority = profile data;
  no env-side enable/disable). Story 13's "missing optional secret degrades gracefully" is
  likewise superseded — no degrade mechanism exists. The requirements doc is already flagged as
  awaiting replacement
  ([delivery status](../../tickets/README.md)); no edit here — the ticket's resolutions are the
  fresher authority.
- Profile-as-config-file, plugin discovery, optional sets and symmetric set selection —
  [#26](../../concerns.md#26-provider--calculator-plugin-scaffolding) / [0125](../../tickets/01-0125-supported-python-embedding.md).
  The *first* named shipped set (`builtin`) lands here; everything beyond it stays #26's.
- [#35](../../concerns.md#35-calculator-satisfiability-vs-optional-provider-degrade) — the
  calculator-vs-optional-provider collision has no boot-time customer after this ticket (no
  optional providers at boot). It stays open for a future optional-plugin story.
- Storeless producers and self-homogenization — [#37](../../concerns.md#37-storeless-materialized-producers-and-read-back-homogenization)
  (widened this align); nothing here moves the binder's store rules.
- The ledger rides this injection path next ([0124](../../tickets/01-0130-vendor-call-ledger.md));
  the Mongo connection string is the second slot consumer ([0130](../../tickets/01-0130-mongo-obs-source.md)).
- No migration: the operator-visible key spelling is unchanged (`METEOSCAPE_TWC_API_KEY`), and a
  leftover `METEOSCAPE_OPEN_METEO_ENABLED` is simply inert (nothing but a declared impl's secret
  name is read). Tidying it is hygiene, not a requirement; `.env.example` documents the surviving
  vocabulary. Env-tunable per-offering settings are **not** provided — that arrives with the
  config file ([0125](../../tickets/01-0125-supported-python-embedding.md)) or is declared in code.
