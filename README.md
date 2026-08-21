# Meteoscape

[![version](https://img.shields.io/badge/version-0.1.0-blue.svg)](./pyproject.toml)
[![CI](https://github.com/dveyarangi/meteoscape/actions/workflows/ci.yml/badge.svg)](https://github.com/dveyarangi/meteoscape/actions/workflows/ci.yml)
[![license: MIT](https://img.shields.io/badge/license-MIT-green.svg)](./LICENSE)
[![Python 3.14](https://img.shields.io/badge/python-3.14-blue.svg)](https://www.python.org/)

**One normalized weather forecast across configured providers, with provenance and freshness on
every parameter.**

Meteoscape is a weather-resolution engine served through MCP. It translates vendor-specific data
into canonical parameters, selects the best available source, falls back when a source fails,
retains fresh results in process, and reports where each value came from.

## Status

Meteoscape is under active v1 development. The shipped surface is a local stdio MCP server with one
tool, `forecast_hourly`, backed by keyless Open-Meteo. A supported Python facade and an HTTP surface
are planned but are not public APIs yet.

→ [Current capabilities and delivery status](./docs/tickets/README.md#available-today)

## Quick start

You need [uv](https://docs.astral.sh/uv/) and Python 3.14 or newer.

```bash
uv sync
uv run meteoscape
```

This starts a stdio MCP server; it does not open a network port. Configure your MCP client to launch
`uv run meteoscape` from the repository root. The shipped Open-Meteo profile requires no API key.

## MCP tool

```text
forecast_hourly(latitude, longitude, parameters?, start?, end?)
```

- `latitude` and `longitude` select one point.
- `parameters` optionally selects from `air_temperature`, `precipitation`, `relative_humidity`,
  `cloud_cover`, `wind_speed`, and `wind_direction`. Omit it to request every served parameter.
- `start` and `end` optionally bound the forecast window with ISO 8601 datetimes. Omit both to
  request from now through the available horizon.

Example arguments:

```json
{
  "latitude": 32.0853,
  "longitude": 34.7818,
  "parameters": ["air_temperature", "precipitation", "wind_speed"]
}
```

The response contains a shared hourly `valid_time` axis and one block per served parameter. Each
block carries canonical-unit values plus `provenance.source` and `provenance.exp`, the freshness
expiration. Missing readings are JSON `null`.

→ [Complete MCP request, response, and error contract](./docs/edge/mcp.md#contract)

## How it works

1. Provider adapters translate vendor data into Meteoscape's canonical coverage model.
2. The resolver admits compatible producers and applies the configured selection/fallback policy.
3. Retentive reservoirs reuse fresh holdings and refill them when they expire.
4. Surface adapters expose the resolved coverage without leaking vendor-specific semantics.

The recursive abstraction behind these steps is the **Manifold**: projection produces another
Manifold until a requested domain is sampled into a concrete Coverage.

→ [Architecture](./docs/architecture.md) · [Glossary](./docs/glossary.md)

## Configuration

The shipped profile is declared in [`src/meteoscape/server.py`](./src/meteoscape/server.py). Profile
composition belongs in code; environment variables carry secrets only. Keyed offerings read one
secret at `METEOSCAPE_<IMPL>_<SLOT>` and refuse startup when that declared secret is missing.

→ [Environment example](./.env.example) · [Configuration architecture](./docs/architecture.md#config-binders-weaver)

## Development

```bash
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run pytest
```

Live provider parity checks are opt-in:

```bash
uv run pytest tests/parity
```

## Documentation

- [Documentation map](./docs/README.md) — where each kind of project truth lives
- [Product roadmap](./docs/product-roadmap.md) — direction and sequencing
- [v1 requirements](./docs/v1-requirements.md) — release contract
- [Canonical parameters](./docs/parameters.md) — quantities, units, and conventions
- [Open concerns](./docs/concerns.md) — deliberately unresolved design seams

## License

[MIT](./LICENSE)
