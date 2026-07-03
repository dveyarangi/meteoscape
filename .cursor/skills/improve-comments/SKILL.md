---
name: improve-comments
description: Write or improve code base comments
---


# Comment Guide for LLM-Generated Code

## Core Rule

Comments should explain **intent, constraints, and danger**.

They should not translate code into English.

A good comment answers questions the code cannot answer clearly by itself:

* Why does this exist?
* Why was this approach chosen?
* Why was an obvious alternative rejected?
* What domain rule is being enforced?
* What invariant must remain true?
* What external constraint shapes this code?
* What danger should future maintainers notice?

## First Prefer Clear Code

Before adding a comment, check whether the idea can be expressed better through:

* a clearer name
* a smaller function
* a stronger type
* a better module boundary
* a more explicit interface
* a simpler control flow

If the code can be clarified directly, improve the code instead of adding a comment.

## Good Comments Explain Why

Good comments explain reasoning, not mechanics.

```python
# We prefer freshness over provider priority here because stale frost data is dangerous.
```

```python
# Invariant: all ranges in a Coverage share the same geometry.
```

```python
# Visual Crossing reports some hourly values in local time; normalize before merging.
```

## Bad Comments Repeat the Code

Avoid comments that simply narrate what the next line already says.

```python
# Increment i
i += 1
```

```python
# Loop over providers
for provider in providers:
    ...
```

```python
# Check if provider can answer the request
if provider.can_answer(selection):
    ...
```

These comments add noise without adding understanding.

## Comment Stable Knowledge

Prefer comments about things that are unlikely to change accidentally:

* domain rules
* invariants
* protocol contracts
* vendor quirks
* non-local consequences
* safety assumptions
* ordering requirements
* rejected design alternatives

Avoid comments that describe tiny implementation details likely to rot.

## Comment Where Wrong Assumptions Are Likely

Use comments when a future reader may make a plausible but wrong assumption.

```python
# Do not reorder these rules: later checks assume rain risk was already classified.
```

```python
# We do not cache raw vendor JSON here: cache readers need canonical Coverage semantics.
```

```python
# This module normalizes vendor weather semantics.
# It must not perform provider selection or fallback.
```

## Public API Comments

Public API comments should explain correct usage, expectations, and contract boundaries.

They should describe:

* what the caller may assume
* what the caller must provide
* what errors mean
* what is intentionally not guaranteed

Example:

```python
# Returns canonical Coverage in the provider's native geometry.
# If the selection specifies a lattice, the provider may homogenize onto that lattice.
```

## Internal Comments

Internal comments should explain why the implementation has this shape.

They are useful for:

* tricky domain logic
* external API weirdness
* performance-sensitive choices
* surprising ordering
* compatibility constraints
* intentionally ugly but necessary code

## TODO Comments

A TODO must name a concrete missing action.

Bad:

```python
# TODO: clean this horrible mess later
```

Good:

```python
# TODO: split provider normalization from HTTP retry policy.
```

Good TODOs should be actionable, specific, and easy to search.

## Avoid Comment Apologies

Do not use comments to excuse unclear code.

Bad:

```python
# Sorry, this is ugly but it works.
```

Better:

```python
# Provider returns mixed local/UTC timestamps; keep this branch until upstream fixes export format.
```

## Preferred Comment Targets

Prefer comments above:

* modules
* classes
* functions
* public APIs
* tricky blocks
* invariants
* dangerous assumptions

Avoid dense line-by-line comments.

## Final Checklist

Before keeping a comment, ask:

1. Does it explain something the code cannot express clearly?
2. Will it still be true after small implementation changes?
3. Does it prevent a plausible future mistake?
4. Does it explain intent, constraint, or danger?
5. Is it more useful than improving the code itself?

If yes, keep it.

If not, remove it.

## Summary

Good comments preserve design intent.

Bad comments narrate syntax.

Write comments for the maintainer who understands the language, but does not yet understand the context.

If architecture entry/decision/description already exists, prefer link to docs instead of restating it.