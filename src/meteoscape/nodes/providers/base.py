"""Provider leaf Manifold: the composable fetch pipeline.

A vendor-specific leaf that contributes native, normalized Coverages: adapter (auth / HTTP /
endpoints) + its Normalizer + `CadenceDef` / grid declarations, with a `Clock` injected at build.
Stateless, no storage, no children; authors the Coverage's provenance (a single-fetch `Uniform` plane)
at fetch. Its `capability` is a stable `FootprintCapability` leaf built once from the cadence + clock:
per-parameter footprints with static spatial / Z bounds and a clock-anchored `RollingAxis` on
`valid_time` that rolls with the run anchor (ADR-0003 / ADR-0004). See architecture.md ("Provider").

Also hosts the shared HTTP fetch seam (`Transport` / `FetchRequest` / `HttpxTransport`) used by
vendor leaves.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

import httpx

from ...errors import RuntimeFailure
from ...identity import SourceKey
from ...manifold.capability import Capability
from ...manifold.core import Manifold, Selection


class Provider(ABC):
    @abstractmethod
    async def project(self, selection: Selection) -> Manifold: ...

    @property
    @abstractmethod
    def capability(self) -> Capability: ...

    @property
    @abstractmethod
    def source_key(self) -> SourceKey:
        """This producer's identity — stamped onto atomic provenance; never carries priority."""
        ...


@dataclass(frozen=True)
class FetchRequest:
    """Vendor-neutral relative GET — host lives on the `Transport`."""

    path: str
    params: Mapping[str, str]
    headers: Mapping[str, str] = field(default_factory=dict)


@runtime_checkable
class Transport(Protocol):
    """Fetch seam: relative request in, decoded JSON out; faults raise `RuntimeFailure`."""

    async def fetch(self, request: FetchRequest) -> object: ...


class HttpxTransport:
    """httpx-backed `Transport` — connect-level retries; every fault → `RuntimeFailure`."""

    def __init__(
        self,
        base_url: str,
        *,
        timeout: float = 10.0,
        retries: int = 2,
    ) -> None:
        self.base_url = base_url
        self.timeout = timeout
        self.retries = retries

    async def fetch(self, request: FetchRequest) -> object:
        try:
            async with httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                transport=httpx.AsyncHTTPTransport(retries=self.retries),
            ) as client:
                response = await client.get(
                    request.path,
                    params=dict(request.params),
                    headers=dict(request.headers),
                )
                response.raise_for_status()
                return response.json()
        except RuntimeFailure:
            raise
        except httpx.HTTPStatusError as exc:
            raise RuntimeFailure(
                f"upstream HTTP {exc.response.status_code} for {request.path}"
            ) from exc
        except httpx.TimeoutException as exc:
            raise RuntimeFailure(f"upstream timeout for {request.path}") from exc
        except httpx.TransportError as exc:
            raise RuntimeFailure(f"upstream transport error for {request.path}") from exc
        except ValueError as exc:
            # httpx.Response.json() raises ValueError / JSONDecodeError on non-JSON bodies.
            raise RuntimeFailure(f"upstream non-JSON body for {request.path}") from exc
