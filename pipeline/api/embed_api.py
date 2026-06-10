"""Lightweight query embedding via HuggingFace Inference API.

Used by the FastAPI web service instead of the local sentence-transformers
model, keeping RAM under 512 MB for Render's cheap tier. The overnight cron
job continues using the CPU model in src.embed.

Produces the same 768-dim BGE vectors with the same query prefix, so results
are compatible with stored document embeddings.
"""

from __future__ import annotations

import httpx

from src.config import HF_TOKEN, EMBED_MODEL, BGE_QUERY_PREFIX


async def embed_query_api(query: str) -> list[float]:
    """Embed a query string via the HF Inference API (feature-extraction).

    Applies the BGE query prefix so the resulting vector is compatible
    with document embeddings produced by the CPU model.
    """
    if not HF_TOKEN:
        raise RuntimeError(
            "Missing HF_TOKEN environment variable. "
            "Set it in your .env or Render service environment."
        )

    prefixed = f"{BGE_QUERY_PREFIX}{query}"
    url = f"https://api-inference.huggingface.co/pipeline/feature-extraction/{EMBED_MODEL}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            url,
            headers={"Authorization": f"Bearer {HF_TOKEN}"},
            json={"inputs": prefixed},
        )
        resp.raise_for_status()
        embedding = resp.json()

    # The API returns a nested list for single inputs: [[0.1, 0.2, ...]]
    if isinstance(embedding, list) and len(embedding) == 1 and isinstance(embedding[0], list):
        embedding = embedding[0]

    return embedding
