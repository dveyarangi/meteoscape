# Meteoscape

[![version](https://img.shields.io/badge/version-0.1.0-blue.svg)](./pyproject.toml)
[![CI](https://github.com/dveyarangi/meteoscape/actions/workflows/ci.yml/badge.svg)](https://github.com/dveyarangi/meteoscape/actions/workflows/ci.yml)
[![license: MIT](https://img.shields.io/badge/license-MIT-green.svg)](./LICENSE)
[![Python 3.14](https://img.shields.io/badge/python-3.14-blue.svg)](https://www.python.org/)

## What it is

Meteoscape is a **manifold-based Coverage-resolution engine**: it resolves a request for a
field — weather over a point and time — into one normalized, provenance-stamped **Coverage**,
selecting the best obtainable provider per parameter and falling back on failure. It hides the
hard problems — vendor heterogeneity (shapes, units, geometries), source selection, and
freshness — behind one small, uniform contract, surfaced over **MCP** first.

v1 ships a single objective — the *best view* (best-obtainable source + fallback) over timeline
provider data — exposed as one MCP tool, `get_forecast`, returning an hourly point-forecast
`Timeline` for the core surface parameters (temperature, wind, precipitation, humidity).

See [`docs/architecture.md`](./docs/architecture.md) for the design and
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
