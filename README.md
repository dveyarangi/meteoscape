# MeteoScape

[![version](https://img.shields.io/badge/version-0.1.0-blue.svg)](./pyproject.toml)
[![CI](https://github.com/dveyarangi/meteoscape/actions/workflows/ci.yml/badge.svg)](https://github.com/dveyarangi/meteoscape/actions/workflows/ci.yml)
[![license: MIT](https://img.shields.io/badge/license-MIT-green.svg)](./LICENSE)
[![Python 3.14](https://img.shields.io/badge/python-3.14-blue.svg)](https://www.python.org/)

## What it is

MeteoScape is a **cross-provider weather access layer** for normalized, provenance-stamped weather
answers. Its v1 target is to hide vendor heterogeneity, source selection, fallback, and freshness
behind one small contract, surfaced over **MCP** so an AI agent can ask for weather without integrating
each vendor itself.

> **Current status:** early v1 development. `forecast_hourly` serves the full canonical v1
> parameter set through Open-Meteo — six provider-served parameters plus derived wind
> speed/direction — with per-value source provenance, expiration, and nodata handling. Request
> shaping (free `start`/`end` windows), second-provider fallback, retentive caching, and off-grid
> read-back are still ahead. See the [v1 delivery status](./docs/tickets/README.md) for the
> authoritative capability matrix and execution order.

## v1 target

- **One API, every vendor** — canonical units and geometry; integrate once, not once per vendor.
- **Best-source selection with automatic fallback** — the best obtainable provider per
  parameter, falling back on failure so a single vendor outage doesn't break the request.
- **Caching & freshness** — a fresh repeat request is served from cache with no vendor call,
  cutting latency and vendor API usage; every value carries an `expiration`.
- **Provenance on every value** — which provider/run produced each parameter, and how fresh.
- **Derived parameters, not just pass-through** — some parameters are computed rather than
  relayed: v1 serves wind speed/direction from canonical wind components, so you get a
  consistent answer no matter how each vendor represents wind. User-defined derivations
  (dewpoint, heat index, …) are roadmap.
- **MCP-native** — one tool, `forecast_hourly`, returning an hourly point-forecast `Timeline`
  for the core surface parameters (temperature, wind, precipitation, humidity, cloud cover).

Beyond v1, the roadmap includes usage monitoring and quota/rate-limit control over vendor APIs,
user-defined derived parameters, and surfaces beyond MCP.

**Under the hood.** MeteoScape is organized around a recursive **Manifold** algebra that gives
normalization, selection, caching, and homogenization one uniform contract. See
[`docs/architecture.md`](./docs/architecture.md) for the design and
[`docs/v1-requirements.md`](./docs/v1-requirements.md) for the concrete v1 release contract. The
[documentation map](./docs/README.md) identifies the owner of each kind of project information.

## Setup

Requires [uv](https://docs.astral.sh/uv/). It manages the Python toolchain and the virtualenv.

```bash
# install the pinned environment (including dev tooling)
uv sync

# run checks
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run pytest

# run the entry point
uv run meteoscape
```

Configuration is via environment / typed settings (Pydantic Settings). The current keyless
Open-Meteo path requires no provider secret, and a missing `SENTRY_DSN` disables error reporting
without failing startup. Complete key-present/key-absent multi-provider construction is tracked by
[ticket 008](./docs/tickets/008-config-secrets-degrade.md).

## Requirements

- **Python 3.14+**
- **[uv](https://docs.astral.sh/uv/)** for packaging and environment management

Runtime stack: Pydantic v2 · httpx · FastMCP · numpy · xarray · sentry-sdk. Tooling: ruff ·
pyright · pytest · respx · hypothesis. See [`pyproject.toml`](./pyproject.toml) for exact pins
and [`docs/cicd.md`](./docs/cicd.md) for the DevOps setup.

## License

[MIT](./LICENSE)
