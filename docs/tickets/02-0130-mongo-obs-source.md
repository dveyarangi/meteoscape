# Mongo obs source

- **Status:** Planned — its own align precedes implementation; it settles the
  [#45](../concerns.md#45-the-collector-schema-is-a-contract-meteoscape-depends-on-but-does-not-own)
  mitigations (fixtures-as-contract, schema version marker if cheap, ownership statement) and the
  observation-source semantics still open below.
- **Blocks:** [Mongo forecast-run archive source](./02-0134-forecast-run-archive-source.md) (shares
  the transport and registry), [correction calculator](./02-0140-correction-calculator.md).
- **Outcome:** Hourly station observations from the operator's Collector database served through
  the projection algebra as a read-only private source, with per-parameter provenance naming the
  observation origin.

## Parent

Release 02 is contract-deferred (no requirements doc yet — [delivery status](./README.md)); the
owning durable context is [product-roadmap → Priority candidate after v1](../product-roadmap.md#priority-candidate-after-v1-local-station-validation-and-bias-correction)
and concern [#45](../concerns.md#45-the-collector-schema-is-a-contract-meteoscape-depends-on-but-does-not-own).

## What to build

The first private source ([glossary → Collector](../glossary.md)): a leaf projecting the operator's
collector MongoDB **read-only** — the first non-HTTP transport, so the acquire/decode seam split
inside "provider" happens here, not by pre-design. It maps the collector's two observation schemas
(the regional station-network documents carrying `raw` and `method`; legacy `ibm_hod`) onto
canonical parameters, reads the `stations` registry and `state` freshness doc for capability, and
serves past-facing windows: T reach ends at the newest retained observation, not at a forecast
horizon.

New semantics this shape introduces (decided at this ticket's align, not before):

- **Past-facing capability and freshness** — what `expiration` means for an observation (it does
  not age like a model run), and how collection recency (`state.last_observation_time`) narrates.
- **Station-located geometry** — observations exist at *their* stations, not at the request's
  point; how a request point resolves against the registry (exact station key vs the off-grid
  homogenization path) is this align's to decide.
- **The schema contract** — #45's mitigations become concrete here: pinned integration fixtures
  sampled from real documents are the contract test; the collector owns the schema, this source
  adapts.

**Out of scope:** the forecast collections
([forecast-run archive source](./02-0134-forecast-run-archive-source.md)); any live station
*endpoint* — permanently embedder-plug-in territory per #45 and
[#26](../concerns.md#26-provider--calculator-plugin-scaffolding); any write path to the collector
database.

## Acceptance criteria

- [ ] A request over an archived window at a registered station location serves hourly observation
      series for the mapped canonical parameters, with per-parameter provenance naming the
      observation origin.
- [ ] Capability reflects the registry and retained data honestly: an unregistered location or a
      window beyond retained observations is declined as capability, never served empty or padded.
- [ ] Both collector observation schemas are served through one canonical mapping; fields the
      collector does not write (e.g. precipitation, currently absent) are absent from capability,
      not null-filled.
- [ ] The collector schema contract is pinned by integration fixtures sampled from real documents —
      a collector-side schema change fails the suite, never silently misreads at runtime.
- [ ] The source is read-only by construction, pinned by a guard (no write/update/insert reaches
      the Mongo client).
- [ ] The align's resolutions (obs freshness semantics, station-located geometry resolution, #45
      mitigations) are recorded in their durable homes before implementation starts.

## Blocked by

- [supported Python embedding surface](./01-0125-supported-python-embedding.md) (active) — the
  embedder is this source's first consumer; its align settles the construction/config experience
  this source's offering plugs into.

## Parent scope addressed

- Roadmap "Priority candidate after v1": *project the operator's Collector database (station
  registry + hourly observations) as an observation source.*
