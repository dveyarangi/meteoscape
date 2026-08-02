# RFC 0007 · 2026-07-25 · Provider parity checks — implementation plan

Implementation plan for [m3](../../tickets/done/01-0080-provider-parity-checks.md). The *meaning* of a Provider
parity check — independence rules, comparison semantics, evidence expectations — is owned by the
[Provider authoring guide](../../provider-authoring.md) and is not restated here. **Living document** —
being built up during the 2026-07-25 align session; decisions land here as they crystallise.

**Scope in one line:** give the live parity suite an executable home and a documented opt-in
command, and land the Open-Meteo parity check as the reference implementation, without changing the
deterministic gate.

## Design decisions (aligned 2026-07-25)

1. **Home and opt-in are structural, not conventional.** The existing suite moves whole
   (`git mv`) to `tests/deterministic/` — the folder name makes physical the term the docs already
   own ("the deterministic suite", [provider-authoring.md](../../provider-authoring.md)) — and live
   parity checks live beside it in `tests/parity/`. `pyproject.toml` gains
   `testpaths = ["tests/deterministic"]`, so the default `uv run pytest` **cannot collect** a live
   test: no marker discipline, no `addopts` deselection. The opt-in command is
   `uv run pytest tests/parity`, selecting one provider with `-k <provider-id>`; an explicit path
   argument overrides `testpaths`, so no config override is needed.
   - Rejected: a top-level `parity/` directory (parity does not warrant a root-level home);
     `@pytest.mark.parity` + `addopts = "-m 'not parity'"` (opt-in by convention — one forgotten
     marker is a live network call in CI, and `addopts` silently rewrites what `uv run pytest`
     means); `--ignore=tests/parity` via `addopts` (applies even to explicit runs, so the opt-in
     command would need to un-ignore itself).
   - Mechanical consequences: `pythonpath` becomes `["src", "tests/deterministic", "tests"]` —
     `tests/deterministic` keeps the 13 `from fakes import ...` files working with zero import
     edits; `tests` makes `parity` an importable package (`parity.comparison`,
     `parity.readers.open_meteo`), which the engine's own deterministic unit tests and the guard
     test require (`tests/parity/` and `tests/parity/readers/` each carry an `__init__.py`).
     Ruff's `src` gains `tests/deterministic` so `fakes` stays a first-party isort root (otherwise
     I001 wants a third-party blank line before `meteoscape`). CI's bare `uv run pytest` is steered
     by `testpaths` with no workflow change, and `pyright` / `ruff` configs already cover `tests`
     recursively — which means **parity code sits inside the default static gates**: it is
     type-checked and linted on every PR without ever executing (that is what makes the "pyright
     green without network" criterion apply to it; do not exclude `tests/parity` from `pyright`).

2. **The harness is a library coupled through data; the comparison boundary is the MCP payload.**
   Parity hunts drift between our canned assumptions and the live producer, so its value is
   proportional to how much of the transformation chain sits between the compared points — the
   comparison therefore happens at the **wire payload** (in-process `fastmcp.Client` over
   `build_mcp_app`, the deterministic e2e's shape minus `respx`), the only neutral, stable data
   Meteoscape emits. Comparing at the Gateway would couple the harness to `Coverage` /
   `ParameterData` internals that algebra refactors legitimately reshape, and would skip the edge
   (unit labels, nodata-as-`null`, time formatting) where drift-prone assumptions live.
   - Shared engine: `tests/parity/comparison.py` — a `ReferenceTimeline` shape (per-parameter
     canonical-unit values on a valid-time axis, with nodata positions), a per-parameter comparison
     spec (`exact` | `absolute(tol)` | `circular(tol)`), and an evidence-rich assert reporting the
     ticket's required failure fields.
   - Per-provider contribution: a reference reader in `tests/parity/readers/<provider>.py` that
     satisfies the reader contract and **imports no `meteoscape` code**, plus a plain pytest file
     wiring root + reader + spec. Auth, clients, sync/async, and request idioms stay inside the
     provider's own files — the "must not impose" clause.
   - The independence rule is **enforced, not reviewed-for**: a deterministic **guard test** (in the
     default suite — importing a reader needs no network) imports every `parity.readers.*` module
     **in a subprocess** and asserts no `meteoscape*` module was loaded. The subprocess is
     required, not optional: the suite's own process has long since imported `meteoscape` through
     other tests, so an in-process `sys.modules` assertion would always fail. Iterating
     `pkgutil.iter_modules` over the package means every future provider's reader is guarded with
     no per-provider registration. This also closes the transitive hole: a reader could reach
     `meteoscape` via `fakes` without violating the rule's letter — the guard catches that too.
   - Rejected: a `ParityCase` template the harness drives (the first paginated or auth-handshaked
     reference fetch fights the lifecycle); **raw vendor responses as the comparison target**
     (upstream of parse → normalize → convert → derive, so it validates only the fetch, and the
     canonicalizing converter it would still need gravitates toward reusing Meteoscape conversion
     helpers — the tautology). Raws are retained as **failure evidence** only.
   - When the Python embedding facade ([#39](../../concerns.md#39-python-embedding-surface-and-public-failures))
     lands as a second public surface, it becomes the natural second parity boundary; the engine
     never does.

3. **The Open-Meteo reference reader is a minimal direct JSON fetch, with the suitability
   justification recorded.** The [authoring guide](../../provider-authoring.md) prefers an official
   client *when suitable*; the official `openmeteo-requests` client is judged unsuitable for the
   reference role: it speaks FlatBuffers (failure evidence becomes opaque binary where the guide
   wants reproducible artifacts), adds three dev dependencies, and for Open-Meteo the public JSON
   API is itself the canonical documented interface — a ~30-line `httpx`-plus-parse reader *is*
   reading the official surface and stays fully auditable, which matters for code whose whole
   authority rests on independence. Recording the justification keeps the guide's preference rule
   intact for future providers.
   - Accepted residual risk: correlated request-building (a reader author copying our provider's
     query params). Bounded by writing the reader against Open-Meteo's documentation and by the
     no-`meteoscape`-imports rule (decision 2).
   - Bounded request: Berlin `52.52, 13.41` (the manual-check and e2e precedent), all six product
     parameters, **the surface's default window** (currently the fixed 168 h horizon; after
     [003c](../../tickets/01-0110-request-shaping.md), the reach-end default — the comparison aligns by
     declared valid-times, so it is insensitive to which), UTC. A second location (southern
     hemisphere / negative longitude, exercising sign conventions) is a cheap follow-on, not part
     of m3.

4. **Comparison spec, calm floor, and the run-boundary race.**
   - Per-parameter spec: **exact** for `air_temperature`, `relative_humidity`, `precipitation`,
     `cloud_cover` (numeric pass-through; the 2026-07-24 manual check matched exactly, so any
     inexactness is a finding, not noise); **`absolute(1e-6 m/s)`** for `wind_speed` and
     **`circular(1e-6°)`** for `wind_direction` (km/h→m/s conversion plus the speed/dir → u/v →
     speed/dir roundtrip; true error ~1e-13 relative, so 1e-6 is generous yet catches real
     conversion drift). Nodata positions match exactly in both directions.
   - **Calm floor — an engine fix, not a parity workaround.** `wind_from_uv` currently emits
     `atan2(-0,-0) % 360 = 180.0°` when `u = v = 0` — an arbitrary angle presented as data. The
     vendor rounds speed to 0.1 km/h, so a reported `0.0` becomes exactly `u = v = 0` at
     normalization and the direction is genuinely unrecoverable. The Calculator masks
     `wind_direction` to `present=False` below `CALM_SPEED_FLOOR`, a named epsilon constant
     (~1e-9 m/s) in `calculators/wind.py` guarding the degenerate math — deliberately **not** a
     meteorological calm convention (WMO 0.5 m/s would discard real model direction; that is a
     product policy this ticket does not own). The parity spec's carve-out — reference speed at or
     below the floor ⇒ expect payload `null` for direction — imports the same constant in the **test
     file** (which composes the root and may import `meteoscape`; only the reader is import-clean),
     so the two thresholds cannot drift.
   - Architecture check (done at align): no ADR or architecture.md change is needed — calm-direction
     nodata is an instance of the existing concept ([architecture §Failure, nodata, and
     availability](../../architecture.md#failure-nodata-and-availability): "a producer succeeded but
     has no value at a cell"), joining vendor nulls (002c) as v1's second nodata source; and
     [#31](../../concerns.md#31-positional-alignment-is-asserted-never-checked)'s "element-wise,
     input domain unchanged" claim about `wind_from_uv` survives (the floor masks `present`, it
     never changes lengths). `parameters.md` carries the parameter-level note (ticket Docs to
     sync).
   - Alignment: by declared ISO valid-times. Meteoscape is called first; the reference request is
     bounded to the payload's window (that is the guide's "align by declared valid times", not a
     dependence). A Meteoscape tick missing from the reference is a failure, never a silent skip.
   - **Run-boundary race: retry the whole comparison once, composing a fresh root per attempt** —
     a vendor model run publishing between the two fetches produces a legitimate mismatch; twice in
     a row is improbable enough that the second failure is real. The fresh root is load-bearing,
     not hygiene: once [006](../../tickets/01-0130-retentive-store-freshness.md) lands retention, a retry
     through the *same* gateway would serve the cached first-run values against a re-fetched new
     run and could never clear the boundary — a guaranteed false alert in exactly the case retry
     exists for. `compose()` is cheap; each attempt builds its own. Run pinning /
     reference-metadata machinery is deliberately deferred until the simple policy demonstrably
     fails (TODO recorded in the ticket's follow-on section).

5. **Failure evidence rides two channels, split by audience.** The assertion message carries the
   judging summary — provider, bounded request, a compact first-N mismatch table (parameter, valid
   time, reference vs. Meteoscape, difference), total counts. A failure-time **evidence bundle**
   on disk carries reproduction — both requests, both raw responses (vendor JSON verbatim, MCP
   payload), the full diff — under a gitignored `tests/parity/_artifacts/<timestamp>-<provider>/`,
   its path stated in the assertion message. The decisive fact: parity evidence is **perishable** —
   the vendor forecast that produced a mismatch rolls over within hours, so an
   assertion-message-only failure from CI or an overnight run would be unreproducible by the time a
   human reads it. Retention must happen at failure time.
   - Redaction is mechanical and shared: the evidence writer takes the secrets mapping the root was
     composed with and scrubs those values from everything it writes (URLs, headers, bodies). A
     no-op for keyless Open-Meteo; the rule exists before the first secret-bearing Provider (TWC,
     004) rather than being retrofitted.
   - **Mechanism (aligned 2026-07-25):** serialize each artifact to text, then substring-replace
     every non-empty secret **value** before writing the file (same scrub on any summary text that
     could echo request material). Nested URLs/headers/bodies are covered without a key catalogue
     or a recursive object walker. Empty secret strings are skipped (would otherwise erase the
     whole artifact). Replacement token: `"***"`.

## Code shapes

### `calculators/wind.py` — the calm floor (decision 4)

```python
CALM_SPEED_FLOOR = 1e-9
"""m/s. Below this, u = v = ±0 and the reconstructed direction is `atan2` of signed zeros —
a numerically arbitrary angle (today: 180.0). An epsilon guard on the degenerate math,
deliberately not a meteorological calm convention (that would be product policy)."""

# in wind_from_uv, after `speed` and `present` are built:
base = present if present is not None else (True,) * n
present_direction = [p and s > CALM_SPEED_FLOOR for p, s in zip(base, speed, strict=True)]
# WIND_SPEED keeps `present`; WIND_DIRECTION uses ParameterData.of(..., present_direction)
# so an all-present mask elides to None. `direction` values are computed unconditionally;
# the mask is what withholds them (ADR-0002: a non-present value slot is an ignored placeholder).
```

### `tests/parity/comparison.py` — the shared engine (decision 2, 4, 5)

Imports **nothing from `meteoscape`** (so importing a reader that uses `ReferenceTimeline` stays
guard-clean). All types are frozen dataclasses:

```python
class Exact: ...                     # lossless pass-through: any difference is a finding
class Absolute: tol: float           # |a − b| ≤ tol, canonical unit
class Circular: tol_deg: float       # d = |a − b| % 360; min(d, 360 − d) ≤ tol_deg
Rule = Exact | Absolute | Circular

class CalmRule:
    speed_parameter: str             # "wind_speed" (canonical m/s in both inputs)
    direction_parameter: str         # "wind_direction"
    floor: float                     # the test file passes CALM_SPEED_FLOOR here

class ParitySpec:
    rules: Mapping[str, Rule]        # keyed by product parameter name
    calm: CalmRule | None

class ReferenceTimeline:
    valid_time: Sequence[datetime]                 # UTC-aware hourly ticks
    values: Mapping[str, Sequence[float | None]]   # canonical units; None = nodata

class Mismatch:
    parameter: str; valid_time: datetime
    reference: float | None; meteoscape: float | None
    difference: float | None                       # None ⇔ a nodata-position mismatch
    # For a calm-violation row (payload direction present below the floor): `reference` is None
    # (the *expectation* — payload must be null), not the vendor's supplied direction; that
    # vendor datum remains in the evidence bundle's reference response.

class ParityReport:
    mismatches: Sequence[Mismatch]; compared: int; skipped_calm: int
    # ok ⇔ not mismatches
    # compared = count of (tick × parameter) pairs that reached a value-or-nodata judgment;
    # excludes calm skips and missing-tick rows (those are structural, not cell judgments).

def compare(payload, reference, spec) -> ParityReport
def write_evidence(provider_id, artifacts, secrets) -> Path   # → _artifacts/<UTC stamp>-<provider>/
def format_summary(provider_id, request_desc, report, evidence_path | None, *, secrets=None) -> str
```

`compare` semantics, exhaustively — one behavior per branch, no discretion:

1. Parse `payload["valid_time"]` with `datetime.fromisoformat` (handles the `Z` form). Index the
   reference by its (already UTC-aware) ticks. Every payload tick must exist in the reference —
   a missing tick is a `Mismatch` with both values `None` for every compared parameter at that
   tick position (never a silent skip). The reference may be a superset. Missing-tick rows do
   **not** increment `compared`.
2. Per parameter in `spec.rules`, per tick, reading the payload block's `values[i]` (`null` ⇒
   `None`) against the reference series:
   - **Missing payload block (aligned 2026-07-25):** if `name` is absent from `payload`, raise
     `ValueError` naming the parameter — a structural incomplete comparison, not a value
     mismatch (do not emit per-tick `Mismatch` rows or silently skip).
   - **Calm carve-out first** (only for `calm.direction_parameter`): if the reference value of
     `calm.speed_parameter` at this tick is not `None` and `<= floor` (complement of the
     calculator's `s > CALM_SPEED_FLOOR` keeps-present predicate, so the boundary tick cannot
     disagree), expect the payload direction to be `None` — a present payload value is a
     `Mismatch` with `reference=None` (expectation, not the vendor direction), `meteoscape` =
     the present payload value, `difference=None`; either way the value comparison is skipped
     and `skipped_calm` incremented (`compared` is not). The vendor direction remains available
     in the evidence bundle.
   - **Nodata:** exactly one side `None` → `Mismatch(difference=None)`. Both `None` → pass.
     Both paths increment `compared`.
   - **Both present:** apply the rule (`Exact` / `Absolute` / `Circular` as defined above);
     increments `compared`.
3. `write_evidence` creates `_artifacts/<YYYYMMDDTHHMMSSZ>-<provider>/` **module-relative**
   (`Path(__file__).parent` of `comparison.py`, i.e. always `tests/parity/_artifacts/` regardless
   of the invoking CWD) holding
   `meteoscape_request.json`, `meteoscape_payload.json`, `reference_request.json`,
   `reference_response.json` (verbatim body), and `diff.json` (all mismatches). Each file's text
   is scrubbed by substring-replacing every non-empty secret value in the mapping (Open-Meteo:
   empty mapping, no-op). Replacement token: `"***"`.
4. `format_summary` reports provider, request, per-parameter mismatch counts, the first **10**
   mismatches per parameter (parameter, valid time, reference, Meteoscape, difference), and the
   evidence path when one was written. Summary inputs that may carry request material are scrubbed
   the same way before formatting.

### `tests/parity/readers/open_meteo.py` — the reference reader (decision 3)

Imports stdlib + `httpx` + `parity.comparison` (for `ReferenceTimeline`) — **never `meteoscape`**.
Owns its own constants; sharing the provider's would defeat the point:

```python
BASE_URL = "https://api.open-meteo.com/v1/forecast"      # the reader's own, not the provider's
HOURLY = ("temperature_2m", "relative_humidity_2m", "precipitation",
          "cloud_cover", "wind_speed_10m", "wind_direction_10m")
EXPECTED_UNITS = {"temperature_2m": "°C", "relative_humidity_2m": "%", "precipitation": "mm",
                  "cloud_cover": "%", "wind_speed_10m": "km/h", "wind_direction_10m": "°"}
TO_PRODUCT = {"temperature_2m": "air_temperature", ..., "wind_speed_10m": "wind_speed", ...}

class RawEvidence: url: str; body: str                    # verbatim, for the evidence bundle

def fetch_reference(latitude, longitude, start, end) -> tuple[ReferenceTimeline, RawEvidence]
    # sync httpx GET: latitude, longitude, hourly=",".join(HOURLY),
    # start_hour/end_hour = ISO minutes of the payload window, timezone=UTC. raise_for_status.
def parse_reference(body: str) -> ReferenceTimeline       # pure; deterministic-tested
    # 1. hourly_units must equal EXPECTED_UNITS — on drift, raise ValueError naming the field
    #    (unit drift is itself a parity finding, reported loudly rather than mis-converted).
    # 2. naive vendor times → UTC-aware.
    # 3. conversions, independently: wind_speed_10m / 3.6 → m/s; all others numeric identity;
    #    JSON null → None. Keys mapped through TO_PRODUCT.
```

The reader is sync (`httpx.Client`): it runs inside a test, blocking is fine, and async would buy
nothing but ceremony.

### `tests/parity/test_open_meteo.py` — the live check (decisions 2–5)

**Profile pin (aligned 2026-07-25):** do **not** call bare `Settings().profile()`.
`Settings.offerings()` already appends a `twc` offering whenever `METEOSCAPE_TWC_API_KEY` is
set, and today's catalogue has no TWC leaf — so a developer `.env` with that key makes
`compose` raise `CompositionError` before any forecast runs. Pin via constructor override
(init wins over env/dotenv in pydantic-settings; same idiom as `tests/test_config.py`):

```python
settings = Settings(open_meteo_enabled=True, twc_api_key=None)
# settings.profile() → OM-only offerings + wind calc + store knobs
# settings.secrets() → {}  (correct for keyless OM; redaction is a no-op)
```

004 generalizes this pattern for TWC / multi-Provider envs; m3 does not add a
`Settings.profile_for(...)` API.

```python
SPEC = ParitySpec(
    rules={"air_temperature": Exact(), "relative_humidity": Exact(),
           "precipitation": Exact(), "cloud_cover": Exact(),
           "wind_speed": Absolute(tol=1e-6), "wind_direction": Circular(tol_deg=1e-6)},
    calm=CalmRule("wind_speed", "wind_direction", CALM_SPEED_FLOOR),   # imported from meteoscape
)
ATTEMPTS = 2   # decision 4: retry-once, fresh root per attempt

@pytest.mark.asyncio
async def test_open_meteo_parity() -> None:
    settings = Settings(open_meteo_enabled=True, twc_api_key=None)
    for attempt in range(ATTEMPTS):
        payload = await _forecast_payload(settings)
        start, end = _window(payload["valid_time"])
        reference, raw = fetch_reference(52.52, 13.41, start, end)
        report = compare(payload, reference, SPEC)
        if report.ok:
            return
    evidence = write_evidence(
        "open-meteo",
        {
            "meteoscape_request": {...},
            "meteoscape_payload": payload,
            "reference_request": {...},
            "reference_response": raw.body,   # verbatim vendor body string
            "diff": report,
        },
        settings.secrets(),
    )
    pytest.fail(format_summary("open-meteo", ..., report, evidence))
```

**`_forecast_payload(settings)`** (aligned inventable notes): mirror
`tests/deterministic/test_e2e_forecast.py` minus `respx` — each call must `compose` a **fresh**
root (`settings.profile()`, `PROVIDER_CATALOG`, `CALCULATOR_CATALOG`, `settings.secrets()`,
`Metronome()`, `StoreFactory()`), `build_mcp_app(gateway, clock, settings.default_horizon)`,
then `async with Client(app)` → `call_tool("forecast_hourly", {"latitude": 52.52,
"longitude": 13.41})` → return `.data`. Do not cache gateway/app across retry attempts.

**`_window`:** parse first/last `payload["valid_time"]` ISO-Z strings to UTC-aware datetimes for
the reference reader's `start`/`end`.

No sleep between attempts (a run boundary has already passed by the time the first comparison
finishes). Evidence is written only for the final failure (last attempt's payload/raw). The test
file — and only the test file — imports `meteoscape` (`compose`, `build_mcp_app`, `Settings`,
`Metronome`, `CALM_SPEED_FLOOR`).

### `write_evidence` artifacts dict

Caller supplies a mapping whose keys match the five filenames (sans `.json`):
`meteoscape_request`, `meteoscape_payload`, `reference_request`, `reference_response`, `diff`.
JSON-serializable objects are dumped; `reference_response` is the verbatim vendor body string
(written as a `.json` file name but content may be raw JSON text from the wire). After dump,
substring-scrub per decision 5.

### Reader time bridge

Open-Meteo `start_hour` / `end_hour` use `%Y-%m-%dT%H:%M` (no `Z`, no seconds) — same wire form
as the Provider leaf. The reader duplicates that format locally; it must not import the
Provider's helper.

### `ParityReport.ok`

`@property` → `not self.mismatches`.

### The guard test — `tests/deterministic/test_parity_reader_guard.py`

Subprocess as decided above: `sys.executable -c` with `PYTHONPATH` set to `src` + `tests` joined
by `os.pathsep`, cwd the repo root, importing every `parity.readers.*` via
`pkgutil.iter_modules`, then asserting no `sys.modules` top-level name is `meteoscape`; the
parent test asserts returncode 0 and surfaces the subprocess output on failure. Green on an
empty readers package (stage 1); stays green as readers arrive.

## Implementation stages

Each stage ends with `uv run ruff check . && uv run ruff format --check . && uv run pyright &&
uv run pytest` green. TDD (red → green) applies where a deterministic test can drive the code;
the live test itself cannot be red-first (network), noted at stage 5.

1. **Layout move** (no behavior change): `git mv` everything under `tests/` into
   `tests/deterministic/`; create `tests/parity/` + `tests/parity/readers/` with `__init__.py`;
   pyproject `testpaths` / `pythonpath` per decision 1; `.gitignore` +
   `tests/parity/_artifacts/`. Suite green, count unchanged.
2. **Calm floor** — RED: a case in `tests/deterministic/nodes/test_wind_calculator.py`
   (existing `point_timeline_domain` fixture; `u = v = 0` input → `wind_direction` not present,
   `wind_speed` present with `0.0`; a small-but-above-floor case stays present). Update the
   existing `test_wind_round_trips_open_meteo_encoding` case that includes `speeds=[0.0, …]` —
   after the floor, calm ticks expect `wind_direction` not present (speed still round-trips).
   GREEN: `CALM_SPEED_FLOOR` + mask in `wind.py`. Same commit: the `parameters.md` wind_direction
   note (docs land with code).
3. **Comparison engine** — RED: `tests/deterministic/test_parity_comparison.py` — exact
   mismatch; `Absolute` at/over tol; `Circular` wraparound (359.9999995 vs 0.0000005 passes at
   1e-6); nodata mismatch in each direction; both-nodata pass; calm carve-out (expected `None`
   passes, present value fails, `skipped_calm` counts); missing payload tick fails; **missing
   payload parameter block raises**; evidence bundle contents + secret scrubbing (`tmp_path`,
   fake secrets embedded in a URL string); `format_summary` field coverage. GREEN:
   `comparison.py`.
4. **Reader** — RED: `tests/deterministic/test_parity_reader_open_meteo.py` over
   `parse_reference` with a canned vendor JSON string (values mapped and converted, km/h → m/s,
   `null` → `None`, naive → aware; unit drift raises naming the field) — canned input is
   deterministic-legal, it is the *live fetch* that is not. Plus the guard test (green on
   arrival unless the reader violates it — a rule test, not a feature test). GREEN:
   `readers/open_meteo.py`.
5. **Live check**: `tests/parity/test_open_meteo.py` as shaped above. Not in CI, cannot be
   red-first (network); its assertion logic is what stages 3–4 already proved. Acceptance is one
   documented manual run: `uv run pytest tests/parity` against the live vendor.
6. **Docs sync + status**: the ticket's "Docs to sync" rows (module-layout, provider-authoring
   command link, cicd note; parameters.md already landed with stage 2), tickets/README m3 row →
   Done, ticket + this RFC → `done/`.

## Scope limits and follow-ups

- **Single location, single window** — Berlin, default window. A southern-hemisphere /
  negative-longitude case is the first follow-on when wanted.
- **TWC parity (004)**: m3's Open-Meteo live check already pins via
  `Settings(open_meteo_enabled=True, twc_api_key=None)` (env-stable OM-only). When 004 adds TWC,
  each parity test pins its under-test Provider the same way (constructor override or a later
  shared helper if duplication bites) — that generalization is 004's parity work, not m3's.
- **Retry policy TODO** and **scheduled/changed-provider automation**: the ticket's follow-on
  section; deliberately absent here.
- **`fakes.py` reachable from parity code** via `pythonpath` — tolerated, guarded (decision 2's
  guard test catches the only harmful case: transitively importing `meteoscape`).
