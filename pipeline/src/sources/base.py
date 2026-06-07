"""The pluggable Source interface.

Adding a new feed (RSS, arXiv, web search) means writing a class that
implements `fetch()` and returns a list of `Article`. Nothing else in the
pipeline changes. The runner just iterates over whatever sources are
registered.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..models import Article


@runtime_checkable
class Source(Protocol):
    """Anything that can produce Articles.

    Implementations:
      - HackerNewsSource  (Phase 1)
      - RSSSource         (Phase 2)
      - ArxivSource       (Phase 2/3)
      - WebSearchSource   (Phase 7, agentic chat only)
    """

    name: str  # short identifier, used as Article.source prefix

    async def fetch(self) -> list[Article]:
        """Pull the latest items and normalize them into Articles."""
        ...