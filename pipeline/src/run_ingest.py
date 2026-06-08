"""Ingestion entrypoint — the cron job target.

Runs every registered source, collects Articles, upserts them to Supabase,
then runs the full-text extraction pass for articles missing body text.

Local run:   python -m src.run_ingest
On Render:   set as the Cron Job's command.
"""

from __future__ import annotations

import asyncio

from .config import RSS_FEEDS
from .db import upsert_articles
from .extract import run_extraction
from .models import Article
from .sources.hackernews import HackerNewsSource
from .sources.rss import RSSSource

# Register sources here.
SOURCES = [
    HackerNewsSource(),
    *(RSSSource(name, url) for name, url in RSS_FEEDS),
]


async def gather_articles() -> list[Article]:
    results: list[Article] = []
    for source in SOURCES:
        try:
            articles = await source.fetch()
            print(f"[{source.name}] fetched {len(articles)} articles")
            results.extend(articles)
        except Exception as exc:
            print(f"[{source.name}] ERROR: {exc} — skipping source")
    return results


async def _run() -> None:
    print("Starting ingestion...", flush=True)
    articles = await gather_articles()
    if not articles:
        print("No articles fetched; nothing to write.")
        return

    print(f"Upserting {len(articles)} articles to Supabase...", flush=True)
    stats = upsert_articles(articles)
    print(f"Wrote to DB: {stats['upserted']} upserted ({len(articles)} total).")

    # Phase 2: fill raw_text for articles that don't have it yet.
    print("\nStarting full-text extraction...", flush=True)
    ext_stats = await run_extraction()
    print(
        f"Extraction complete: {ext_stats['extracted']} extracted, "
        f"{ext_stats['failed']} failed, {ext_stats['total']} total."
    )


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
