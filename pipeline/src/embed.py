"""Embedding pass — Phase 3.

Loads the BGE model once (lazy singleton), chunks articles that have raw_text
but no chunks yet, embeds the chunks, and inserts them into Supabase.

BGE asymmetry: stored documents get NO prefix; queries get the instruction
prefix defined in config.BGE_QUERY_PREFIX.
"""

from __future__ import annotations

from .chunk import chunk_text
from .config import EMBED_MODEL, EMBED_BATCH_SIZE, BGE_QUERY_PREFIX
from .db import (
    fetch_articles_with_text,
    fetch_article_ids_with_chunks,
    insert_chunks,
)

# ---------------------------------------------------------------------------
# Lazy model singleton — sentence_transformers (and torch) are imported on
# first use, not at module load time, so non-embedding code paths stay fast.
# ---------------------------------------------------------------------------

_model = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        print(f"[embed] loading model {EMBED_MODEL} …", flush=True)
        _model = SentenceTransformer(EMBED_MODEL)
        print("[embed] model loaded", flush=True)
    return _model


# ---------------------------------------------------------------------------
# Public embedding helpers
# ---------------------------------------------------------------------------

def embed_documents(texts: list[str]) -> list[list[float]]:
    """Embed document texts (no instruction prefix for BGE)."""
    model = _get_model()
    vectors = model.encode(
        texts,
        batch_size=EMBED_BATCH_SIZE,
        show_progress_bar=False,
        normalize_embeddings=True,
    )
    return vectors.tolist()


def embed_query(query: str) -> list[float]:
    """Embed a single query string with the BGE instruction prefix."""
    model = _get_model()
    vector = model.encode(
        BGE_QUERY_PREFIX + query,
        normalize_embeddings=True,
    )
    return vector.tolist()


# ---------------------------------------------------------------------------
# Embedding pass (called from run_ingest)
# ---------------------------------------------------------------------------

def run_embedding() -> dict[str, int]:
    """Chunk and embed articles that have text but no chunks yet.

    Returns {"embedded": N, "skipped": M, "total": T}.
    """
    articles = fetch_articles_with_text()
    total = len(articles)
    if total == 0:
        print("[embed] no articles with text found", flush=True)
        return {"embedded": 0, "skipped": 0, "total": 0}

    already_chunked = fetch_article_ids_with_chunks()
    to_embed = [a for a in articles if a["id"] not in already_chunked]
    skipped = total - len(to_embed)

    if not to_embed:
        print(f"[embed] all {total} articles already embedded", flush=True)
        return {"embedded": 0, "skipped": skipped, "total": total}

    print(
        f"[embed] {len(to_embed)} articles to embed "
        f"({skipped} already done, {total} total)",
        flush=True,
    )

    model = _get_model()
    tokenizer = model.tokenizer
    embedded = 0

    for art in to_embed:
        raw = art.get("raw_text") or ""
        if not raw.strip():
            continue

        pieces = chunk_text(raw, tokenizer)
        if not pieces:
            continue

        texts = [text for _, text in pieces]
        vectors = embed_documents(texts)

        rows = [
            {
                "article_id": art["id"],
                "chunk_index": ci,
                "chunk_text": ct,
                "embedding": vec,
            }
            for (ci, ct), vec in zip(pieces, vectors)
        ]

        try:
            insert_chunks(rows)
            embedded += 1
        except Exception as exc:
            print(
                f"[embed] SKIP article {art['id']}: "
                f"chunk insert failed ({exc})",
                flush=True,
            )
            continue

        if embedded % 10 == 0:
            print(
                f"[embed] progress: {embedded}/{len(to_embed)} articles",
                flush=True,
            )

    print(
        f"[embed] done: {embedded} articles embedded, "
        f"{skipped} skipped, {total} total",
        flush=True,
    )
    return {"embedded": embedded, "skipped": skipped, "total": total}
