"""Full-text extraction pass — Phase 2.

Runs AFTER ingestion. Fetches the URL for every article that has a URL but
no raw_text yet, extracts the article body with trafilatura, and writes it
back to Supabase.

Best-effort: pages behind paywalls, JS-only renderers, or dead links are
logged and skipped — the article row is kept for its metadata/title.
"""

from __future__ import annotations

import asyncio

import httpx
import trafilatura

from .config import EXTRACT_CONCURRENCY, EXTRACT_DELAY, EXTRACT_USER_AGENT
from .db import fetch_articles_missing_text, update_article_text


async def run_extraction() -> dict[str, int]:
    """Fetch + extract raw_text for all articles missing it.

    Returns {"extracted": N, "failed": M, "total": T}.
    """
    rows = fetch_articles_missing_text()
    total = len(rows)
    if total == 0:
        print("[extract] no articles need extraction", flush=True)
        return {"extracted": 0, "failed": 0, "total": 0}

    print(f"[extract] {total} articles need text extraction", flush=True)

    sem = asyncio.Semaphore(EXTRACT_CONCURRENCY)
    extracted = 0
    failed = 0

    async def _extract_one(row: dict, client: httpx.AsyncClient) -> bool:
        nonlocal extracted, failed
        async with sem:
            try:
                resp = await client.get(
                    row["url"],
                    follow_redirects=True,
                    timeout=20.0,
                )
                resp.raise_for_status()
            except (httpx.HTTPError, httpx.InvalidURL) as exc:
                print(
                    f"[extract] SKIP {row['source']} id={row['id']}: "
                    f"fetch failed ({type(exc).__name__})",
                    flush=True,
                )
                failed += 1
                return False
            finally:
                await asyncio.sleep(EXTRACT_DELAY)

            # trafilatura is CPU-bound — run in a thread.
            text = await asyncio.to_thread(trafilatura.extract, resp.text)
            if not text:
                print(
                    f"[extract] SKIP {row['source']} id={row['id']}: "
                    f"trafilatura returned nothing",
                    flush=True,
                )
                failed += 1
                return False

            try:
                update_article_text(row["id"], text)
            except httpx.HTTPError as exc:
                print(
                    f"[extract] SKIP {row['source']} id={row['id']}: "
                    f"DB update failed ({exc})",
                    flush=True,
                )
                failed += 1
                return False

            extracted += 1
            if extracted % 10 == 0:
                print(
                    f"[extract] progress: {extracted} extracted, "
                    f"{failed} failed / {total} total",
                    flush=True,
                )
            return True

    async with httpx.AsyncClient(
        headers={"User-Agent": EXTRACT_USER_AGENT},
    ) as client:
        await asyncio.gather(*(_extract_one(row, client) for row in rows))

    print(
        f"[extract] done: {extracted} extracted, {failed} failed, {total} total",
        flush=True,
    )
    return {"extracted": extracted, "failed": failed, "total": total}
