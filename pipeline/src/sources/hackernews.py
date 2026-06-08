"""Hacker News ingester — Phase 1 source.

Hits the public HN Firebase API (no auth needed):
  - Fetch item IDs from top/new/best feeds
  - Dedupe IDs across feeds (significant overlap)
  - Fan out item fetches with bounded concurrency
  - Normalize each item into an Article
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import httpx

from ..config import HN_CONCURRENCY, HN_FEEDS, HN_LIMIT_PER_FEED
from ..models import Article

_BASE = "https://hacker-news.firebaseio.com/v0"


class HackerNewsSource:
    name: str = "hackernews"

    async def fetch(self) -> list[Article]:
        sem = asyncio.Semaphore(HN_CONCURRENCY)
        print("[hackernews] starting fetch...", flush=True)

        async with httpx.AsyncClient(timeout=30) as client:
            # 1. Grab item IDs from each feed, dedupe across feeds.
            unique_ids: set[int] = set()
            for feed in HN_FEEDS:
                print(f"[hackernews] fetching {feed}...", flush=True)
                resp = await client.get(f"{_BASE}/{feed}.json")
                resp.raise_for_status()
                ids: list[int] = resp.json()
                unique_ids.update(ids[:HN_LIMIT_PER_FEED])
                print(f"[hackernews] {feed}: got {len(ids)} ids", flush=True)

            print(f"[hackernews] {len(unique_ids)} unique items to fetch", flush=True)

            # 2. Fan out item fetches.
            done = 0

            async def _fetch_item(item_id: int) -> Article | None:
                nonlocal done
                async with sem:
                    try:
                        r = await client.get(f"{_BASE}/item/{item_id}.json")
                        r.raise_for_status()
                    except httpx.HTTPError:
                        return None
                    finally:
                        done += 1
                        if done % 25 == 0:
                            print(f"[hackernews] fetched {done}/{len(unique_ids)} items", flush=True)
                    data = r.json()
                    if data is None or data.get("type") != "story":
                        return None
                    return _to_article(data)

            results = await asyncio.gather(
                *(_fetch_item(i) for i in unique_ids)
            )

        print(f"[hackernews] fetch complete", flush=True)
        return [a for a in results if a is not None]


def _to_article(item: dict) -> Article:
    ts = item.get("time")
    return Article(
        source="hackernews",
        external_id=str(item["id"]),
        title=item.get("title", ""),
        url=item.get("url"),
        author=item.get("by"),
        score=item.get("score"),
        num_comments=item.get("descendants"),
        published_at=datetime.fromtimestamp(ts, tz=timezone.utc) if ts else None,
        metadata={"hn_type": item.get("type")},
    )
