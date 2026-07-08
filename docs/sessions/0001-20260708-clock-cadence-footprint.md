# 0001 · 2026-07-08 · Clock, cadence & the footprint axis

## Work done

- **Naming settled**: the run-timing declaration is `CadenceDef` (not "cadence model"); the time source
  is `Clock` (interface) · `Metronome` (running, floors to a tick) · `StoppedClock` (test double).
  Renamed the concept across the docs (ADR-0002/0003/0004, architecture, glossary, concerns, ideas,
  v1-requirements, module-layout).
- **New code** (all pure, testable):
  - `clock.py` — `Clock` / `Metronome` / `StoppedClock` + `floor_to` (module `_EPOCH`, aware-UTC).
  - `manifold/cadence.py` — `CadenceDef {Δ, L, max_lead}` → `anchor`/`expiration`/`valid_time`, plus
    `RollingAxis` (its clock-relative `Axis` face; `extent = cadence.valid_time(clock.now())`).
- **Footprint/axis design resolved**: the `Clock` is a **build-time** dependency injected into
  `Provider` leaves (like a logger), never threaded through `project`. The Provider builds **one stable**
  `FootprintCapability`; only `RollingAxis.extent` recomputes (cheap arithmetic). Rejected the earlier
  provider `_memo` (made the Provider stateful for no gain).
- **Layout (Option D)**: `RollingAxis` lives in `cadence.py`, not `domain.py`. `FootprintDomain.axes`
  only references the base `Axis`, so `domain.py` is now **pure geometry** with zero clock/cadence
  imports and no `TYPE_CHECKING` cycle. Dependency direction: `clock ← domain ← cadence`.
- **Drift fixed**: `RollingAxis` retargeted from `{lead, retention, now}` to `{cadence, clock}`, matching
  the ADR-0003 cadence anchor model.
- **Toolchain**: added `[tool.pyright]` (`pythonVersion = "3.14"`, venv) — the version errors were a
  missing-config artifact, not a syntax problem. pyright/ruff clean on all touched files.

## Open questions / continuation

- **Concrete cadence numbers** — per-provider `{Δ, L, max_lead}` defaults, and preferring a provider's
  **real** reference/availability signal when exposed. Still [concern #18]; v1 ships conservative guesses.
- **Metronome perf memo** — deferred `TODO(perf)` in `clock.py`: monotonic-gated `(floored, deadline)`
  cache so a request resolves one `now` (one syscall) with within-request consistency. Measured as <1%
  vs provider I/O; build only if a profiler flags it.
- **Provider not implemented** — `nodes/providers/base.py` is still an ABC. A concrete Provider must hold
  `cadence: CadenceDef` + `clock: Clock`, build the stable `FootprintCapability` (spatial/Z
  `ContinuousAxis` + `valid_time` `RollingAxis`), and stamp provenance from `cadence.anchor(clock.now())`.
  The Weaver must inject the `Clock` at build. → issues 001 / 002.
- **Domain seams** — `FootprintDomain.contains` / `intersect` (and the other reps) are still
  `NotImplementedError`; footprint containment lands with Provider behaviour.
- **Clock invariant** — all clocks must return **aware-UTC** (baked into `floor_to` via `_EPOCH`);
  `StoppedClock` instances in tests must honour it.
