"""Every job source implements this protocol; the pipeline treats them uniformly."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..models import RawPosting


@runtime_checkable
class SourceAdapter(Protocol):
    name: str

    async def fetch(self) -> list[RawPosting]: ...
