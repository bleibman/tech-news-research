"""Daily digest generation — Phase 5.

Selects top HN stories by time-decayed score, deduplicates via embeddings,
generates LLM summaries, and writes a finished markdown digest to the
``digests`` table.  No live inference needed at read time.

Entry point: ``generate_digest()``
"""

from __future__ import annotations

import math
from datetime import datetime, timezone

from .config import (
    DIGEST_LOOKBACK_HOURS,
    DIGEST_STORY_COUNT,
    DIGEST_SCORE_HALFLIFE_HOURS,
    DIGEST_DEDUP_THRESHOLD,
    DIGEST_SUMMARY_MAX_TOKENS,
    DIGEST_SUMMARY_TEMPERATURE,
    SYNTHESIS_MODEL,
    SYNTHESIS_FALLBACK_MODEL,
)
from .db import (
    fetch_hn_articles_recent,
    fetch_chunk_embeddings_for_articles,
    upsert_digest,
)


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def _time_decayed_score(
    score: int | None,
    published_at: str | None,
    now: datetime,
    halflife_hours: float = DIGEST_SCORE_HALFLIFE_HOURS,
) -> float:
    """Exponential time-decay: ``score * 0.5^(age_hours / halflife)``."""
    if not score:
        return 0.0
    if not published_at:
        return 0.0

    pub = datetime.fromisoformat(published_at)
    if pub.tzinfo is None:
        pub = pub.replace(tzinfo=timezone.utc)
    age_hours = (now - pub).total_seconds() / 3600
    if age_hours < 0:
        age_hours = 0
    return score * math.pow(0.5, age_hours / halflife_hours)


# ---------------------------------------------------------------------------
# Deduplication via embeddings
# ---------------------------------------------------------------------------

def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Dot product — embeddings are pre-normalized by the embedding model."""
    return sum(x * y for x, y in zip(a, b))


def _deduplicate(
    articles: list[dict],
    embeddings: dict[int, list[float]],
    threshold: float = DIGEST_DEDUP_THRESHOLD,
) -> list[dict]:
    """Greedy dedup: keep articles in order, skip if too similar to a kept one."""
    kept: list[dict] = []
    kept_embs: list[list[float]] = []

    for art in articles:
        emb = embeddings.get(art["id"])
        if emb is None:
            # No embedding — keep it (can't compare)
            kept.append(art)
            continue

        is_dup = False
        for k_emb in kept_embs:
            if _cosine_similarity(emb, k_emb) > threshold:
                is_dup = True
                break
        if not is_dup:
            kept.append(art)
            kept_embs.append(emb)

    return kept


# ---------------------------------------------------------------------------
# LLM summarization
# ---------------------------------------------------------------------------

_SUMMARY_SYSTEM_PROMPT = """\
You are a tech news summarizer. Write a concise 2-3 sentence summary of the \
article provided. Stick to what the article says — do not add opinions or \
outside knowledge. Do NOT include citations — the caller handles that."""


def _summarize_article(article: dict, model: str | None = None) -> str:
    """Generate a short summary of a single article via the HF Inference API."""
    from .synthesize import _get_client

    client = _get_client()
    target_model = model or SYNTHESIS_MODEL

    # Truncate body text to fit context budget (~8k chars ≈ 2k tokens)
    body = (article.get("raw_text") or "")[:8000]
    title = article.get("title", "Untitled")
    user_message = f"Title: {title}\n\nArticle text:\n{body}"

    def _call(m: str) -> str:
        response = client.chat_completion(
            model=m,
            messages=[
                {"role": "system", "content": _SUMMARY_SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            max_tokens=DIGEST_SUMMARY_MAX_TOKENS,
            temperature=DIGEST_SUMMARY_TEMPERATURE,
        )
        return response.choices[0].message.content

    try:
        return _call(target_model)
    except Exception as exc:
        if target_model != SYNTHESIS_FALLBACK_MODEL and model is None:
            print(
                f"[digest] {target_model} failed ({exc}), "
                f"falling back to {SYNTHESIS_FALLBACK_MODEL}",
                flush=True,
            )
            return _call(SYNTHESIS_FALLBACK_MODEL)
        raise


# ---------------------------------------------------------------------------
# Markdown formatting
# ---------------------------------------------------------------------------

def _format_digest(date_str: str, summaries: list[dict]) -> tuple[str, str, list[dict]]:
    """Build the final markdown digest from a list of {article, summary} dicts.

    Returns (title, content_md, citations) matching the DB schema.
    """
    title = f"Tech News Digest — {date_str}"
    lines = [f"# {title}", ""]

    citations: list[dict] = []
    for i, item in enumerate(summaries, 1):
        art = item["article"]
        summary = item["summary"]
        art_title = art.get("title", "Untitled")
        url = art.get("url", "")
        score = art.get("score") or 0
        comments = art.get("num_comments") or 0

        lines.append(f"## {i}. {art_title}")
        lines.append("")
        lines.append(summary)
        lines.append("")
        lines.append(f"[Read more]({url}) | {score} points | {comments} comments")
        lines.append("")

        citations.append({
            "title": art_title,
            "url": url,
            "score": score,
            "num_comments": comments,
            "article_id": art.get("id"),
        })

    return title, "\n".join(lines), citations


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def generate_digest() -> dict:
    """Generate today's digest: select, dedup, summarize, write to DB.

    Returns stats dict with keys: stories, candidates, deduped, date.
    """
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d")

    # 1. Fetch recent HN articles
    print("[digest] Fetching recent HN articles...", flush=True)
    articles = fetch_hn_articles_recent(hours=DIGEST_LOOKBACK_HOURS)
    print(f"[digest] Found {len(articles)} candidates.", flush=True)

    if not articles:
        print("[digest] No articles found — skipping digest.", flush=True)
        return {"stories": 0, "candidates": 0, "deduped": 0, "date": date_str}

    # 2. Score with time decay and sort
    for art in articles:
        art["_decayed_score"] = _time_decayed_score(
            art.get("score"), art.get("published_at"), now
        )
    articles.sort(key=lambda a: a["_decayed_score"], reverse=True)

    # 3. Fetch embeddings for dedup
    article_ids = [a["id"] for a in articles]
    print("[digest] Fetching embeddings for dedup...", flush=True)
    embeddings = fetch_chunk_embeddings_for_articles(article_ids)
    print(f"[digest] Got embeddings for {len(embeddings)} articles.", flush=True)

    # 4. Deduplicate
    deduped = _deduplicate(articles, embeddings, threshold=DIGEST_DEDUP_THRESHOLD)
    removed = len(articles) - len(deduped)
    if removed:
        print(f"[digest] Removed {removed} near-duplicate(s).", flush=True)

    # 5. Take top N
    top = deduped[:DIGEST_STORY_COUNT]
    print(f"[digest] Summarizing {len(top)} stories...", flush=True)

    # 6. Summarize each article
    summaries: list[dict] = []
    for j, art in enumerate(top, 1):
        title = art.get("title", "?")
        print(f"  [{j}/{len(top)}] {title[:60]}", flush=True)
        try:
            summary = _summarize_article(art)
        except Exception as exc:
            print(f"  WARN: summary failed for '{title}': {exc}", flush=True)
            summary = f"*(Summary unavailable: {exc})*"
        summaries.append({"article": art, "summary": summary})

    # 7. Format markdown
    title, content_md, citations = _format_digest(date_str, summaries)

    # 8. Upsert to DB
    print("[digest] Writing digest to database...", flush=True)
    upsert_digest(
        digest_date=date_str,
        title=title,
        content_md=content_md,
        citations=citations,
    )

    stats = {
        "stories": len(summaries),
        "candidates": len(articles),
        "deduped": removed,
        "date": date_str,
    }
    print(f"[digest] Done: {stats}", flush=True)
    return stats
