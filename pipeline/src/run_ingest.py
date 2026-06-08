"""Phase 1 entrypoint — the cron job target.

Runs every registered source, collects Articles, upserts them to Supabase.
Later phases add processing/embedding here; for now it's fetch -> store.

Local run:   python -m src.run_ingest
On Render:   set as the Cron Job's command.
"""

from __future__ import annotations

import asyncio

from .db import upsert_articles
from .models import Article
from .sources.hackernews import HackerNewsSource

# Register sources here. Phase 2 appends RSSSource(...), etc.
SOURCES = [HackerNewsSource()]


async def gather_articles() -> list[Article]:
    results: list[Article] = []
    for source in SOURCES:
        articles = await source.fetch()
        print(f"[{source.name}] fetched {len(articles)} articles")
        results.extend(articles)
    return results


def main() -> None:
    print("Starting ingestion...", flush=True)
    articles = asyncio.run(gather_articles())
    if not articles:
        print("No articles fetched; nothing to write.")
        return
    print(f"Upserting {len(articles)} articles to Supabase...", flush=True)
    stats = upsert_articles(articles)
    print(f"Wrote to DB: {stats['upserted']} upserted ({len(articles)} total).")


if __name__ == "__main__":
    main()