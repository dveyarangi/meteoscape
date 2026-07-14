# Meteoscape · DevOps setup

Records the operational/DevOps decisions for the project: toolchain, CI, deployment form, and
observability. The *architecture* contract lives in [`architecture.md`](./architecture.md); this
doc is the layer below it — how the project is built, checked, and run.

## Language & toolchain

- **Python 3.14+**, async throughout (`requires-python = ">=3.14"`).
- **[uv](https://docs.astral.sh/uv/)** for packaging and environment management — it owns the
  Python toolchain, the virtualenv, and the lockfile (`uv.lock`). Chosen over pip/Poetry for its
  single-tool speed and reproducible locked syncs.
- Build backend: `uv_build`.

Quality tooling (pinned in `pyproject.toml`, dev group):

| Concern | Tool |
|---|---|
| Lint | `ruff check` |
| Format | `ruff format` (line length 100, double quotes) |
| Types | `pyright` |
| Tests | `pytest` + `pytest-asyncio` + `pytest-cov` |
| HTTP mocking | `respx` |
| Property tests | `hypothesis` |

## CI pipeline

GitHub Actions — [`.github/workflows/ci.yml`](../.github/workflows/ci.yml). Triggers on push to
`main` and on every pull request; in-flight runs for the same ref are cancelled.

One `build` job on `ubuntu-latest`:

1. `uv sync --locked` — install the exact locked environment.
2. `uv run ruff check .` — lint.
3. `uv run ruff format --check .` — formatting gate.
4. `uv run pyright` — type check.
5. `uv run pytest` — tests.

Remote: `github.com/dveyarangi/meteoscape`.

> The pytest suite includes packaging and MCP-startup smoke coverage, unit and property tests, and
> mocked-provider integration coverage. Last-observed health and outstanding gate failures live in
> the [v1 delivery status](./tickets/README.md); CI remains authoritative.

## Deployment form

**No container in v1.** v1 is a **local stdio MCP server** (FastMCP; HTTP/remote transport
deferred per [`v1-requirements.md`](./v1-requirements.md)) — an MCP client launches the process
over stdio, so there is no long-running network service for a `Dockerfile`/`docker-compose` to
host. Containerization is revisited when the HTTP transport seam is built. Deployment
configuration is out of scope.

## Observability

- **Sentry** (`sentry-sdk`) for error reporting.
- Init seam: [`src/meteoscape/observability.py`](../src/meteoscape/observability.py) — a single
  `init_observability()` the composition root calls once at startup. DSN comes from `SENTRY_DSN`
  (env) or an injected argument.
- **Optional / graceful-degrade**: no DSN ⇒ no-op, the server runs without error reporting —
  the same optional-secret rule v1 applies to provider keys. `METEOSCAPE_ENV` tags the
  environment when set.
- The typed error taxonomy (`bad-request` / `capability-mismatch` / `runtime-failure`) is normal
  control flow, not telemetry; Sentry is for *unexpected* failures initialized at the composition
  root.

## License

[MIT](../LICENSE).
