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
> the [delivery status](./tickets/README.md); CI remains authoritative.

Live Provider parity checks (`uv run pytest tests/parity`) are deliberately **outside CI**:
`testpaths` scopes the default run to `tests/deterministic/`, keeping the gate network-free —
see the [Provider edge record](./edge/provider.md). Enforcement and routing of those checks are
[#41](./concerns.md#41-parity-evidence-is-unenforced-and-unrouted).

**Documentation integrity is gated.** The corpus is deliberately cross-referential — a claim lives
in one document and is cited from the rest — so two guard modules in the deterministic suite
(`test_docs_integrity_guard.py`, `test_docs_conventions_guard.py`) fail the ordinary pytest step
when that structure breaks: a live document's relative link or heading anchor stops resolving; any
tracked file carries a BOM, a stray control character, or a blocklisted invisible codepoint; a code
comment's doc pointer (a `#NN` concern ref, an `ADR-NNNN`, or a `.md` path in its canonical
repo-root form, `docs/edge/provider.md`) stops resolving; the delivery map and the ticket folders
disagree; or a session record's filename and H1 disagree about its number or date. Dated records —
`docs/sessions/`, `docs/tickets/done/`, `docs/rfc/done/`, `docs/dreams/` — are kept as written, so
their *outbound* links are exempt (a README inside such a directory stays gated); byte hygiene has
no exemptions. External URLs are never checked — the gate stays network-free. Policy, exemptions,
and the incident history: [docs-integrity-gate](./tickets/done/01-0127-docs-integrity-gate.md).

Lifecycle moves are mechanical: `uv run python .agents/scripts/move_doc.py SRC DST [SRC DST ...]`
performs the `git mv`, re-depths the moved record's own links, and rewrites live citers (a paired
ticket+RFC close goes in one invocation); the guards then prove the move →
[mechanical record moves](./tickets/done/01-0128-mechanical-record-moves.md).

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
