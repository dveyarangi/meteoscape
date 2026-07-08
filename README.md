# Meteoscape

[![version](https://img.shields.io/badge/version-0.1.0-blue.svg)](./pyproject.toml)
[![CI](https://github.com/dveyarangi/meteoscape/actions/workflows/ci.yml/badge.svg)](https://github.com/dveyarangi/meteoscape/actions/workflows/ci.yml)
[![license: MIT](https://img.shields.io/badge/license-MIT-green.svg)](./LICENSE)
[![Python 3.14](https://img.shields.io/badge/python-3.14-blue.svg)](https://www.python.org/)

## What it is

Meteoscape is a **cross-provider weather access layer**: ask for weather once, over a point
and time, and get back one normalized, provenance-stamped answer — drawn from the best
available vendor, cached, and fetched again only when it goes stale. It hides vendor
heterogeneity (units, shapes, geometries), source selection, and freshness behind one small
contract, surfaced over **MCP** so an AI agent can ask for weather without integrating a
single vendor itself.

**What it gives a caller**

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
- **MCP-native** — one tool, `get_forecast`, returning an hourly point-forecast `Timeline`
  for the core surface parameters (temperature, wind, precipitation, humidity).

**Roadmap.** Usage monitoring and quota/rate-limit control over vendor APIs (a wired-but-null
Gateway seam in v1), user-defined derived parameters, and surfaces beyond MCP.

**Under the hood.** Meteoscape resolves each request through a recursive **Manifold** algebra
that normalizes, selects, caches, and homogenizes provider data behind one uniform contract —
the engine that makes the cross-provider guarantees hold. See
[`docs/architecture.md`](./docs/architecture.md) for the design and
[`docs/v1-requirements.md`](./docs/v1-requirements.md) for the concrete v1 build scope.

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

Configuration is via environment / typed settings (Pydantic Settings). Optional secrets degrade
gracefully — a missing provider key or a missing `SENTRY_DSN` simply disables that capability
rather than failing startup.

## Requirements

- **Python 3.14+**
- **[uv](https://docs.astral.sh/uv/)** for packaging and environment management

Runtime stack: Pydantic v2 · httpx · FastMCP · numpy · xarray · sentry-sdk. Tooling: ruff ·
pyright · pytest · respx · hypothesis. See [`pyproject.toml`](./pyproject.toml) for exact pins
and [`docs/cicd.md`](./docs/cicd.md) for the DevOps setup.

## License

[MIT](./LICENSE)
