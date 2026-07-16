# architecture.md format

`architecture.md` document captures the **technical design**. Unresolved concerns are intentionally **deferred** and listed at the end. Keep in minds that as the document evolves, the deferred concerns may become part of the core document.

## Diagrams — C4 in meaning, regular Mermaid in form

Follow the [C4 model](https://c4model.com/) for the *levels of abstraction*, but render with **plain Mermaid `flowchart`** — **do not** use Mermaid's `C4Context` / `C4Container` / `C4Component` diagram types (their auto-layout is poor). Convey the C4 meaning with a labelled system-boundary `subgraph` and external nodes outside it:

- **System context** (C4 L1) → a `flowchart` with the system as one boxed `subgraph`, the external people/systems around it (callers on one edge, upstream dependencies on the other), and labelled edges for what crosses the boundary.
- **Major components** (C4 L3) → a `flowchart` with the internal components inside a system-boundary `subgraph` and external systems outside; edge labels carry the call/contract crossing each link. A single diagram can double as the dynamic view (label edges with the actual calls, e.g. `project(selection)`).
- **Container level** (C4 L2) — include only when the system is more than one process/deployable; skip it for a single-process service.
- Don't draw the **Code** level (L4) — that belongs in the implementation, not this doc.

## Structure

```md

# Architecture

This document captures the **high-level architecture**. See [`glossary.md`](../glossary.md) for the glossary, [`docs/adr/`](./adr) for recorded decisions, [`docs/concerns.md`](./docs/concerns.md) for open issues and risks. Lower-level concerns are intentionally **deferred** and listed at the end.

> Scope note: everything here is at the architecture/contract level. Where a concrete shape would prematurely lock a deferred decision, we define only the *seam*.
> A fact the design depends on belongs here, but its justification goes to ADRs.
> ADRs are not carved in stone — this is a constantly-evolving project. A recorded rejection must state the real structural load it bears; flag arbitrary rejections rather than treat them as binding.

## Purpose
## Scope / non-scope
## Guiding principles
## System context
## Core concepts
## Major components
## Contract surfaces
## Data / request flow
## Extension points
## Deferred decisions
## Risks / open questions
- should map to [`docs/concerns/`](./docs/concerns) files, in format 
## ADR index

```