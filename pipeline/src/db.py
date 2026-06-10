"""Storage layer — Supabase PostgREST API via httpx.

Phase 1 only writes to `articles`. The upsert is idempotent on the
(source, external_id) unique constraint, so re-running the ingester (which
the overnight cron will do nightly) updates existing rows instead of
duplicating them — score/comment counts refresh, fetched_at bumps.
"""

from __future__ import annotations

from collections.abc import Sequence

import httpx

import json

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
    # Explicit on_conflict tells PostgREST which unique constraint to use
    # (required when the table has more than one unique/pk constraint).
    resp = httpx.post(
        f"{_REST_URL}/articles",
        headers=_HEADERS,
        params={"on_conflict": "source,external_id"},
        json=rows,
        timeout=30.0,
    )
    resp.raise_for_status()

    return {"upserted": len(resp.json())}


def fetch_articles_missing_text() -> list[dict]:
    """Return lightweight dicts for articles that have a URL but no raw_text.

    Used by the extraction pass to know which articles still need body text.
    """
    resp = httpx.get(
        f"{_REST_URL}/articles",
        headers=_HEADERS,
        params={
            "raw_text": "is.null",
            "url": "not.is.null",
            "select": "id,url,source",
        },
        timeout=30.0,
    )
    resp.raise_for_status()
    return resp.json()


def update_article_text(article_id: int, raw_text: str) -> None:
    """Set the raw_text for a single article by its DB id."""
    resp = httpx.patch(
        f"{_REST_URL}/articles",
        headers=_HEADERS,
        params={"id": f"eq.{article_id}"},
        json={"raw_text": raw_text},
        timeout=30.0,
    )
    resp.raise_for_status()


# ---------------------------------------------------------------------------
# Phase 3 — chunks + retrieval
# ---------------------------------------------------------------------------

def fetch_articles_with_text() -> list[dict]:
    """Return articles that have raw_text populated (candidates for embedding).

    Selects only the columns needed by the embedding pass.
    """
    resp = httpx.get(
        f"{_REST_URL}/articles",
        headers=_HEADERS,
        params={
            "raw_text": "not.is.null",
            "select": "id,title,url,source,raw_text",
        },
        timeout=30.0,
    )
    resp.raise_for_status()
    return resp.json()


def fetch_article_ids_with_chunks() -> set[int]:
    """Return the set of article IDs that already have rows in the chunks table.

    Used to skip re-embedding articles on subsequent runs.
    """
    resp = httpx.get(
        f"{_REST_URL}/chunks",
        headers=_HEADERS,
        params={"select": "article_id"},
        timeout=30.0,
    )
    resp.raise_for_status()
    return {row["article_id"] for row in resp.json()}


def insert_chunks(chunks: list[dict]) -> int:
    """Batch-insert chunk rows into the chunks table.

    Each dict must have: article_id, chunk_index, chunk_text, embedding.
    The embedding is a plain list[float] — PostgREST/pgvector handles the
    conversion to the vector type.

    Returns the number of rows inserted.
    """
    if not chunks:
        return 0

    # Use plain-insert headers (no resolution=merge-duplicates, which is
    # only valid for upserts with on_conflict).
    headers = {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }

    # PostgREST expects the embedding as a JSON string like "[0.1,0.2,...]"
    # for vector columns — convert list[float] to string.
    rows = []
    for c in chunks:
        row = dict(c)
        row["embedding"] = str(c["embedding"])
        rows.append(row)

    resp = httpx.post(
        f"{_REST_URL}/chunks",
        headers=headers,
        json=rows,
        timeout=60.0,
    )
    if resp.status_code >= 400:
        print(f"[db] insert_chunks error: {resp.text[:500]}", flush=True)
    resp.raise_for_status()
    return len(resp.json())


def search_chunks(
    query_embedding: list[float], top_k: int = 10
) -> list[dict]:
    """Semantic search via the match_chunks RPC function.

    Returns up to *top_k* chunk dicts with a ``similarity`` score, ordered by
    descending similarity.
    """
    resp = httpx.post(
        f"{_REST_URL}/rpc/match_chunks",
        headers=_HEADERS,
        json={
            "query_embedding": query_embedding,
            "match_count": top_k,
        },
        timeout=30.0,
    )
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# Phase 5 — digest generation
# ---------------------------------------------------------------------------

def fetch_hn_articles_recent(hours: int = 48) -> list[dict]:
    """Fetch recent HN articles with body text, ordered by score descending."""
    from datetime import datetime, timedelta, timezone

    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    resp = httpx.get(
        f"{_REST_URL}/articles",
        headers=_HEADERS,
        params={
            "source": "eq.hackernews",
            "published_at": f"gte.{cutoff}",
            "raw_text": "not.is.null",
            "select": "id,title,url,author,score,num_comments,published_at,raw_text",
            "order": "score.desc.nullslast",
        },
        timeout=120.0,  # large payload — full raw_text for ~200 articles
    )
    resp.raise_for_status()
    return resp.json()


def fetch_chunk_embeddings_for_articles(article_ids: list[int]) -> dict[int, list[float]]:
    """Fetch chunk_index=0 embeddings for a list of article IDs.

    Returns {article_id: embedding_vector}.
    """
    if not article_ids:
        return {}

    ids_str = ",".join(str(i) for i in article_ids)
    resp = httpx.get(
        f"{_REST_URL}/chunks",
        headers=_HEADERS,
        params={
            "article_id": f"in.({ids_str})",
            "chunk_index": "eq.0",
            "select": "article_id,embedding",
        },
        timeout=30.0,
    )
    resp.raise_for_status()

    result = {}
    for row in resp.json():
        emb = row.get("embedding")
        if emb is None:
            continue
        if isinstance(emb, str):
            emb = json.loads(emb)
        result[row["article_id"]] = emb
    return result


def upsert_digest(
    digest_date: str,
    title: str,
    content_md: str,
    citations: list[dict] | None = None,
) -> None:
    """Insert or update a digest row keyed by digest_date."""
    row = {
        "digest_date": digest_date,
        "title": title,
        "content_md": content_md,
        "citations": citations or [],
    }
    resp = httpx.post(
        f"{_REST_URL}/digests",
        headers=_HEADERS,
        params={"on_conflict": "digest_date"},
        json=row,
        timeout=30.0,
    )
    resp.raise_for_status()
