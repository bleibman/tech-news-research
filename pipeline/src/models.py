"""Core data shapes shared across all sources.

Every Source (HackerNews, RSS, arXiv, ...) normalizes its raw items into
the `Article` dataclass below, so the rest of the pipeline (processing,
storage) never has to care where an article came from.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class Article:
    """The common article shape produced by every Source.

    Maps 1:1 to a row in the `articles` table. Fields that a given source
    doesn't provide are simply left as their defaults (None / empty).
    """

    source: str                    # 'hackernews', 'rss:arstechnica', ...
    external_id: str               # source's own ID (HN item id, RSS guid)
    title: str

    url: str | None = None         # canonical link to the article
    author: str | None = None
    raw_text: str | None = None    # full body — filled in Phase 2 (trafilatura)
    score: int | None = None       # HN upvotes / quality signal
    num_comments: int | None = None
    published_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)  # source-specific extras

    def dedupe_key(self) -> tuple[str, str]:
        """Matches the (source, external_id) unique constraint in Postgres."""
        return (self.source, self.external_id)