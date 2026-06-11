"""Full-text extraction pass — Phase 2.

Runs AFTER ingestion. Fetches the URL for every article that has a URL but
no raw_text yet, extracts the article body with trafilatura, and writes it
back to Supabase.

Best-effort: pages behind paywalls, JS-only renderers, or dead links are
logged and skipped — the article row is kept for its metadata/title.

Processes articles in small batches to stay within Render's memory limits.
trafilatura/lxml is a C extension that can corrupt the heap if too many
concurrent parsing threads pile up on a constrained instance.
"""

from __future__ import annotations

import asyncio
import gc

import httpx
import trafilatura

from .config import EXTRACT_CONCURRENCY, EXTRACT_DELAY, EXTRACT_USER_AGENT
from .db import fetch_articles_missing_text, update_article_text

_BATCH_SIZE = 20  # articles per batch — keeps peak RSS low on 512 MB instances


_FETCH_FAILED = object()  # sentinel distinct from trafilatura's None


async def _extract_one(
    row: dict,
    client: httpx.AsyncClient,
    sem: asyncio.Semaphore,
) -> object:
    """Fetch one URL and extract text.

    Returns extracted text (str), None (trafilatura empty), or _FETCH_FAILED.
    """
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
            return _FETCH_FAILED
        finally:
            await asyncio.sleep(EXTRACT_DELAY)

        html = resp.text
        del resp  # free response body before parsing

        # trafilatura is CPU-bound — run in a thread, but only one at a time
        # to avoid lxml heap corruption under memory pressure.
        text = await asyncio.to_thread(trafilatura.extract, html)
        del html
        return text


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

    # Concurrency=2 keeps at most 2 trafilatura/lxml parses in flight,
    # preventing heap corruption on memory-constrained Render instances.
    sem = asyncio.Semaphore(min(EXTRACT_CONCURRENCY, 2))
    extracted = 0
    failed = 0

    async with httpx.AsyncClient(
        headers={"User-Agent": EXTRACT_USER_AGENT},
    ) as client:
        # Process in batches to bound peak memory.
        for batch_start in range(0, total, _BATCH_SIZE):
            batch = rows[batch_start : batch_start + _BATCH_SIZE]

            tasks = [_extract_one(row, client, sem) for row in batch]
            results = await asyncio.gather(*tasks)

            for row, text in zip(batch, results):
                if text is _FETCH_FAILED:
                    failed += 1
                    continue
                if not text:
                    print(
                        f"[extract] SKIP {row['source']} id={row['id']}: "
                        f"trafilatura returned nothing",
                        flush=True,
                    )
                    failed += 1
                    continue

                try:
                    update_article_text(row["id"], text)
                except httpx.HTTPError as exc:
                    print(
                        f"[extract] SKIP {row['source']} id={row['id']}: "
                        f"DB update failed ({exc})",
                        flush=True,
                    )
                    failed += 1
                    continue

                extracted += 1

            print(
                f"[extract] progress: {extracted} extracted, "
                f"{failed} failed / {total} total",
                flush=True,
            )

            # Let the allocator reclaim C-level buffers between batches.
            gc.collect()

    print(
        f"[extract] done: {extracted} extracted, {failed} failed, {total} total",
        flush=True,
    )
    return {"extracted": extracted, "failed": failed, "total": total}
