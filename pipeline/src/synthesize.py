"""LLM synthesis with citation discipline — Phase 4.

Given a user question, retrieves relevant chunks via semantic search and
generates a cited answer using Llama via the HuggingFace Inference API.

Entry point is `ask(question)` which runs the full pipeline:
embed query → search chunks → synthesize cited answer.
"""

from __future__ import annotations

from .config import (
    HF_TOKEN,
    SYNTHESIS_MODEL,
    SYNTHESIS_FALLBACK_MODEL,
    SYNTHESIS_MAX_OUTPUT_TOKENS,
    SYNTHESIS_TOP_K,
    SYNTHESIS_TEMPERATURE,
)
from .db import search_chunks
from .embed import embed_query

# ---------------------------------------------------------------------------
# Lazy client singleton — huggingface_hub is imported on first use so
# non-synthesis code paths (ingestion, embedding) stay fast.
# ---------------------------------------------------------------------------

_client = None


def _get_client():
    global _client
    if _client is None:
        if not HF_TOKEN:
            raise RuntimeError(
                "Missing HF_TOKEN environment variable. "
                "Set it in your .env file with a Hugging Face token that has "
                "Inference API access. See https://huggingface.co/settings/tokens"
            )
        from huggingface_hub import InferenceClient

        _client = InferenceClient(token=HF_TOKEN)
    return _client


# ---------------------------------------------------------------------------
# System prompt — citation-or-abstain discipline
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are a tech news research assistant. Answer the user's question using ONLY \
the provided source excerpts. Follow these rules strictly:

1. Cite sources using numbered references like [1], [2], etc.
2. Every factual claim MUST have a citation. No uncited claims.
3. If the sources do not contain enough information to answer the question, \
say exactly: "I don't have enough information in my sources to answer that."
4. Do NOT fabricate, infer, or use knowledge outside the provided sources.
5. At the end of your answer, include a "Sources:" section listing each \
referenced source with its number, title, and URL.

Format the Sources section like this:
Sources:
[1] Title — URL
[2] Title — URL
"""


# ---------------------------------------------------------------------------
# Context formatting
# ---------------------------------------------------------------------------

def _select_chunks_within_budget(
    chunks: list[dict], budget_chars: int = 24_000
) -> list[dict]:
    """Trim chunks to fit within a character budget (~6000 tokens at 4 chars/token)."""
    selected = []
    total = 0
    for chunk in chunks:
        text = chunk.get("chunk_text", "")
        if total + len(text) > budget_chars:
            break
        selected.append(chunk)
        total += len(text)
    return selected


def _format_context(chunks: list[dict]) -> str:
    """Format retrieved chunks as numbered source blocks for the LLM prompt."""
    blocks = []
    for i, chunk in enumerate(chunks, 1):
        title = chunk.get("title", "Untitled")
        url = chunk.get("url", "")
        source = chunk.get("source", "")
        similarity = chunk.get("similarity", 0)
        text = chunk.get("chunk_text", "")
        blocks.append(
            f"[{i}] {title}\n"
            f"    Source: {source} | URL: {url} | Relevance: {similarity:.3f}\n"
            f"    {text}"
        )
    return "\n\n".join(blocks)


# ---------------------------------------------------------------------------
# Synthesis
# ---------------------------------------------------------------------------

def synthesize(
    question: str,
    chunks: list[dict],
    model: str | None = None,
) -> str:
    """Build prompt from chunks and call the LLM. Returns the model's answer.

    Falls back to SYNTHESIS_FALLBACK_MODEL if the primary model fails.
    """
    client = _get_client()
    target_model = model or SYNTHESIS_MODEL

    selected = _select_chunks_within_budget(chunks)
    if not selected:
        return "I don't have enough information in my sources to answer that."

    context = _format_context(selected)
    user_message = (
        f"Source excerpts:\n\n{context}\n\n"
        f"Question: {question}"
    )

    def _call(m: str) -> str:
        response = client.chat_completion(
            model=m,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            max_tokens=SYNTHESIS_MAX_OUTPUT_TOKENS,
            temperature=SYNTHESIS_TEMPERATURE,
        )
        return response.choices[0].message.content

    try:
        return _call(target_model)
    except Exception as exc:
        error_msg = str(exc)
        if "403" in error_msg or "gated" in error_msg.lower():
            print(
                f"[synthesize] Access denied for {target_model}. "
                f"Visit https://huggingface.co/{target_model} to request access.",
                flush=True,
            )

        # Only fall back if using the default model (not an explicit override)
        if target_model != SYNTHESIS_FALLBACK_MODEL and model is None:
            print(
                f"[synthesize] {target_model} failed ({exc}), "
                f"falling back to {SYNTHESIS_FALLBACK_MODEL}",
                flush=True,
            )
            return _call(SYNTHESIS_FALLBACK_MODEL)
        raise


# ---------------------------------------------------------------------------
# Full pipeline entry point
# ---------------------------------------------------------------------------

def ask(
    question: str,
    model: str | None = None,
    top_k: int | None = None,
    verbose: bool = False,
) -> str:
    """End-to-end: embed question -> retrieve chunks -> synthesize answer."""
    k = top_k or SYNTHESIS_TOP_K

    print("[ask] Embedding query...", flush=True)
    qvec = embed_query(question)

    print(f"[ask] Searching for top {k} chunks...", flush=True)
    chunks = search_chunks(qvec, top_k=k)

    if not chunks:
        return "No relevant sources found. Have you run the ingestion + embedding pipeline?"

    if verbose:
        print(f"\n[ask] Retrieved {len(chunks)} chunks:", flush=True)
        for i, c in enumerate(chunks, 1):
            sim = c.get("similarity", 0)
            title = c.get("title", "?")
            print(f"  [{i}] {sim:.4f} — {title}", flush=True)
        print(flush=True)

    print("[ask] Synthesizing answer...", flush=True)
    return synthesize(question, chunks, model=model)
