"""Build-time profile reach — wiring check, footprint selection, and the `grid` rule (ADR-0007)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from ..identity import CalculatorKey, ProducerKey, SourceKey
from ..manifold.domain import AXIS_ORDER, Domain, Separable
from ..parameters import ParameterId
from .composition import CompositionError, ProfileDef, RegisteredCalculator


def _contains(outer: Domain, inner: Domain) -> bool:
    """Whether `outer` whole-box contains `inner` by per-axis extent containment — not `matches`."""
    if not isinstance(outer, Separable) or not isinstance(inner, Separable):
        return False
    return all(
        outer.axis(name).extent.contains(inner.axis(name).extent)  # type: ignore[arg-type]
        for name in AXIS_ORDER
    )


def _split(left_key: object, left: Domain, right_key: object, right: Domain) -> str:
    """Why two Domains fail to nest, **both directions** — the split is the incomparability.

    A single "failing axis" is a misreport: nested-but-incomparable boxes (`Global x 10 d` vs
    `Europe x 16 d`) each dominate on a *different* axis, and naming only the first one sends an
    operator to the axis where the other candidate is winning.
    """
    assert isinstance(left, Separable) and isinstance(right, Separable)
    parts: list[str] = []
    for name in AXIS_ORDER:
        a = left.axis(name).extent
        b = right.axis(name).extent
        if not a.contains(b):  # type: ignore[arg-type]
            parts.append(f"{right_key} extends beyond {left_key} on {name.value}")
        if not b.contains(a):  # type: ignore[arg-type]
            parts.append(f"{left_key} extends beyond {right_key} on {name.value}")
    return "; ".join(parts)


def _incomparable(
    candidates: Sequence[tuple[object, Domain]],
) -> tuple[tuple[object, Domain], tuple[object, Domain]] | None:
    """First pair nesting neither way — the witness both sites report when selection is unresolved."""
    for i, left in enumerate(candidates):
        for right in candidates[i + 1 :]:
            if not _contains(left[1], right[1]) and not _contains(right[1], left[1]):
                return left, right
    return None


def _names(candidates: Sequence[tuple[object, Domain]]) -> list[str]:
    return [str(key) for key, _ in candidates]


def _contained_in_all(
    candidates: Sequence[tuple[ParameterId, Domain]], *, calculator: CalculatorKey
) -> Domain:
    """Most restrictive Domain — contained in every other (Calculator-site structure, not policy)."""
    if not candidates:
        raise CompositionError(f"calculator {calculator} has no inputs to resolve reach from")
    if len(candidates) == 1:
        return candidates[0][1]

    for _key, domain in candidates:
        if all(_contains(other, domain) for _k, other in candidates):
            return domain

    witness = _incomparable(candidates)
    if witness is None:  # unreachable: extent containment is transitive, so a minimum exists
        raise CompositionError(
            f"calculator {calculator}: no input reach contained in all of {_names(candidates)}"
        )
    (left_key, left), (right_key, right) = witness
    raise CompositionError(
        f"sheared calculator input reaches for {calculator}: "
        f"{_split(left_key, left, right_key, right)}; inputs {_names(candidates)}"
    )


class GridReachRule:
    """The v1 reach rule: the Reach Domain among alternative footprints.

    Containment only — the X/Y-first preference (ADR-0007's one product judgment) is
    **not built**; incomparable candidates raise, pending a regional provider.
    """

    def reach(self, candidates: Sequence[tuple[ProducerKey, Domain]]) -> Domain:
        """Return one candidate's Domain as the promised Reach (never synthesized)."""
        if not candidates:
            raise CompositionError("GridReachRule.reach requires at least one candidate")
        if len(candidates) == 1:
            return candidates[0][1]

        for _key, domain in candidates:
            if all(_contains(domain, other) for _k, other in candidates):
                return domain

        witness = _incomparable(candidates)
        if witness is None:  # unreachable: extent containment is transitive, so a maximum exists
            raise CompositionError(
                f"no containing footprint among {_names(candidates)}; X/Y preference is unbuilt"
            )
        (left_key, left), (right_key, right) = witness
        raise CompositionError(
            f"incomparable reach footprints: {_split(left_key, left, right_key, right)}; "
            f"candidates {_names(candidates)}; X/Y preference is unbuilt"
        )


def resolve_reach(profile: ProfileDef) -> Mapping[ParameterId, Domain]:
    """Per-parameter Reach — inner bound, selected never synthesized. Precondition: validated."""
    rule = GridReachRule()
    sources = profile.sources.sources
    calculators = profile.calculators.calculators
    calc_memo: dict[CalculatorKey, Domain] = {}

    def scoped_of(reg: RegisteredCalculator) -> list[ProducerKey]:
        """Producers that can serve any of `reg.inputs` — mirrors Weaver.producers_for."""
        keys: list[ProducerKey] = [
            key
            for key, registered in sources.items()
            if reg.inputs & registered.provider.footprints.keys()
        ]
        keys.extend(key for key, other in calculators.items() if reg.inputs & other.outputs.keys())
        return keys

    def calculator_footprint(key: CalculatorKey) -> Domain:
        if key in calc_memo:
            return calc_memo[key]
        reg = calculators[key]
        scoped = scoped_of(reg)
        input_reaches = [(inp, reach_over(scoped, inp)) for inp in reg.inputs]
        domain = _contained_in_all(input_reaches, calculator=key)
        calc_memo[key] = domain
        return domain

    def footprint(key: ProducerKey, pid: ParameterId) -> Domain | None:
        if isinstance(key, SourceKey):
            return sources[key].provider.footprints.get(pid)
        reg = calculators[key]
        if pid not in reg.outputs:
            return None
        return calculator_footprint(key)

    def reach_over(producers: Sequence[ProducerKey], pid: ParameterId) -> Domain:
        candidates: list[tuple[ProducerKey, Domain]] = []
        for key in producers:
            domain = footprint(key, pid)
            if domain is not None:
                candidates.append((key, domain))
        return rule.reach(candidates)

    all_producers: list[ProducerKey] = [*sources.keys(), *calculators.keys()]
    served: set[ParameterId] = set()
    for registered in sources.values():
        served.update(registered.provider.footprints)
    for registered in calculators.values():
        served.update(registered.outputs)

    return {
        pid: reach_over(all_producers, pid)
        for pid in served
        if any(footprint(key, pid) is not None for key in all_producers)
    }


def validate_calculators(profile: ProfileDef) -> None:
    """Every calculator input producible and the calculator graph acyclic. Raise CompositionError.

    Runs before `weave`, and is the guard an operator's error comes from — so it must reject exactly
    what the Weaver cannot build. It therefore descends into every upstream calculator **even when a
    source also serves that input**: the Weaver builds a scoped Arbiter over *all* producers of an
    input, so a calculator cycle a source happens to shadow is still an unbuildable graph (and would
    recurse forever in `resolve_reach`, which trusts this pass).
    """
    calculators = profile.calculators.calculators
    path: list[CalculatorKey] = []
    visiting: set[CalculatorKey] = set()
    done: set[CalculatorKey] = set()

    def source_serves(pid: ParameterId) -> bool:
        return any(
            pid in registered.provider.footprints for registered in profile.sources.sources.values()
        )

    def ensure(key: CalculatorKey) -> None:
        if key in done:
            return
        if key in visiting:
            cycle = [*path[path.index(key) :], key]
            raise CompositionError("calculator cycle: " + " -> ".join(str(k) for k in cycle))
        visiting.add(key)
        path.append(key)
        for inp in calculators[key].inputs:
            upstream = [
                other for other, other_reg in calculators.items() if inp in other_reg.outputs
            ]
            if not upstream and not source_serves(inp):
                raise CompositionError(
                    f"calculator {key} input {inp} is not served by any producer"
                )
            for other in upstream:
                ensure(other)
        path.pop()
        visiting.discard(key)
        done.add(key)

    for key in calculators:
        ensure(key)
