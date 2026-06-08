"""Storage layer — Supabase PostgREST API via httpx.

Phase 1 only writes to `articles`. The upsert is idempotent on the
(source, external_id) unique constraint, so re-running the ingester (which
the overnight cron will do nightly) updates existing rows instead of
duplicating them — score/comment counts refresh, fetched_at bumps.
"""

from __future__ import annotations

from collections.abc import Sequence

import httpx

from .config import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
from .models import Article

_REST_URL = f"{SUPABASE_URL}/rest/v1"
_HEADERS = {
    "apikey": SUPABASE_SERVICE_ROLE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "resolution=merge-duplicates,return=representation",
}


def _article_to_row(art: Article) -> dict:
    """Convert an Article to a dict matching the articles table columns."""
    return {
        "source": art.source,
        "external_id": art.external_id,
        "url": art.url,
        "title": art.title,
        "author": art.author,
        "raw_text": art.raw_text,
        "score": art.score,
        "num_comments": art.num_comments,
        "published_at": art.published_at.isoformat() if art.published_at else None,
        "metadata": art.metadata,
    }


def upsert_articles(articles: Sequence[Article]) -> dict[str, int]:
    """Insert-or-update a batch of Articles via PostgREST.

    Uses Prefer: resolution=merge-duplicates which triggers the ON CONFLICT
    behaviour on the (source, external_id) unique constraint.

    Returns {'upserted': count} — PostgREST doesn't distinguish insert vs
    update in the same way raw SQL xmax does, so we report the total.
    """
    if not articles:
        return {"upserted": 0}

    rows = [_article_to_row(art) for art in articles]

    # PostgREST accepts bulk upsert as a JSON array.
    resp = httpx.post(
        f"{_REST_URL}/articles",
        headers=_HEADERS,
        json=rows,
        timeout=30.0,
    )
    resp.raise_for_status()

    return {"upserted": len(resp.json())}
