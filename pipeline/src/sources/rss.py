"""RSS/Atom feed ingester — Phase 2 source.

One instance per feed (Ars Technica, The Verge, TechCrunch, …).
Uses feedparser for parsing and trafilatura for stripping HTML from
inline content when the feed provides it.
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone

import feedparser
import trafilatura

from ..models import Article


class RSSSource:
    """Fetch articles from a single RSS/Atom feed."""

    def __init__(self, feed_name: str, feed_url: str) -> None:
        self.name = f"rss:{feed_name}"
        self._feed_url = feed_url

    async def fetch(self) -> list[Article]:
        print(f"[{self.name}] parsing feed...", flush=True)
        # feedparser is synchronous — run in a thread so we don't block the loop.
        feed = await asyncio.to_thread(feedparser.parse, self._feed_url)

        articles: list[Article] = []
        for entry in feed.entries:
            article = self._entry_to_article(entry)
            if article is not None:
                articles.append(article)

        print(f"[{self.name}] got {len(articles)} entries", flush=True)
        return articles

    def _entry_to_article(self, entry) -> Article | None:
        # external_id: prefer guid/id, fall back to link
        external_id = getattr(entry, "id", None) or getattr(entry, "link", None)
        if not external_id:
            return None

        title = getattr(entry, "title", None)
        if not title:
            return None

        url = getattr(entry, "link", None)
        author = getattr(entry, "author", None)

        # Timestamp: try published_parsed, then updated_parsed
        published_at = None
        time_struct = getattr(entry, "published_parsed", None) or getattr(
            entry, "updated_parsed", None
        )
        if time_struct:
            try:
                published_at = datetime.fromtimestamp(
                    time.mktime(time_struct), tz=timezone.utc
                )
            except (ValueError, OverflowError):
                pass

        # Inline content: if the feed includes full HTML body (>500 chars),
        # extract plain text now so we skip the extraction pass later.
        raw_text = None
        html_body = None
        if hasattr(entry, "content") and entry.content:
            html_body = entry.content[0].get("value", "")
        if not html_body or len(html_body) < 500:
            summary = getattr(entry, "summary", None)
            if summary and len(summary) >= 500:
                html_body = summary

        if html_body and len(html_body) >= 500:
            extracted = trafilatura.extract(html_body)
            if extracted:
                raw_text = extracted

        return Article(
            source=self.name,
            external_id=external_id,
            title=title,
            url=url,
            author=author,
            raw_text=raw_text,
            score=None,
            published_at=published_at,
            metadata={"feed_url": self._feed_url},
        )
