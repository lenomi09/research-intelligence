"""The PaperSource interface (see architecture.md §2.3/§8, ADR-013).

Per ADR-013, even the MVP's manual/local collection input is meant to sit behind
this interface (a trivial PaperSource implementation), not bypass it — so any future
networked source (e.g. arXiv topic search, DISC-003) is a drop-in replacement, not a
rewrite. Sprint 2's only implementation is LocalCollectionPaperSource
(src/infrastructure/paper_sources/local_collection_source.py); nothing outside
src/infrastructure/paper_sources may depend on a specific paper source directly.

Deliberately minimal: no ``search(topic: str)`` method yet, since topic search
(DISC-003) is out of scope this sprint and nothing calls it — see
docs/development-guidelines.md, "don't build for methods nothing calls yet." It can
be added to this ABC (or a subclass) when DISC-003 is actually implemented, without
breaking LocalCollectionPaperSource.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from src.domain.models.paper import Paper


class PaperSourceError(Exception):
    """Raised when a paper source cannot list its papers."""


class PaperSource(ABC):
    """Provides the paper collection to Discovery."""

    @abstractmethod
    def list_papers(self) -> list[Paper]:
        """Return every paper currently available from this source."""
        raise NotImplementedError
