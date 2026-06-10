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
from .embed import run_embedding
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

    # Phase 3: embed articles that have text but no chunks yet.
    print("\nStarting embedding pass...", flush=True)
    emb_stats = run_embedding()
    print(
        f"Embedding complete: {emb_stats['embedded']} embedded, "
        f"{emb_stats['skipped']} skipped, {emb_stats['total']} total."
    )

    # Phase 5: generate the daily digest.
    from .digest import generate_digest

    print("\nStarting digest generation...", flush=True)
    try:
        digest_stats = generate_digest()
        print(
            f"Digest complete: {digest_stats['stories']} stories "
            f"({digest_stats['candidates']} candidates, "
            f"{digest_stats['deduped']} deduped) for {digest_stats['date']}."
        )
    except Exception as exc:
        print(f"Digest generation FAILED: {exc} — pipeline continues.", flush=True)


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
