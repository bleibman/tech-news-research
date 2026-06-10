"""Manual test script for digest generation — Phase 5.

Usage (from pipeline/):
    python test_digest.py              # run all tests
    python test_digest.py --unit       # unit tests only (no DB / LLM)
    python test_digest.py --live       # live DB + LLM tests only
"""

from __future__ import annotations

import argparse
import math
import sys
from datetime import datetime, timezone, timedelta

from src.digest import (
    _time_decayed_score,
    _cosine_similarity,
    _deduplicate,
    _summarize_article,
    generate_digest,
)
from src.db import fetch_hn_articles_recent


# ---------------------------------------------------------------------------
# Unit tests (no network)
# ---------------------------------------------------------------------------

def test_time_decay():
    """Verify exponential decay with known values."""
    print("=== Time-decay scoring ===")
    now = datetime(2025, 6, 10, 12, 0, 0, tzinfo=timezone.utc)

    # Score 100, published exactly now → should equal 100
    result = _time_decayed_score(100, now.isoformat(), now, halflife_hours=12.0)
    print(f"  age=0h, score=100 → {result:.2f} (expected 100.00)")
    assert abs(result - 100.0) < 0.01

    # Score 100, 12 hours ago → should be 50
    pub_12h = (now - timedelta(hours=12)).isoformat()
    result = _time_decayed_score(100, pub_12h, now, halflife_hours=12.0)
    print(f"  age=12h, score=100 → {result:.2f} (expected 50.00)")
    assert abs(result - 50.0) < 0.01

    # Score 100, 24 hours ago → should be 25
    pub_24h = (now - timedelta(hours=24)).isoformat()
    result = _time_decayed_score(100, pub_24h, now, halflife_hours=12.0)
    print(f"  age=24h, score=100 → {result:.2f} (expected 25.00)")
    assert abs(result - 25.0) < 0.01

    # None score → 0
    result = _time_decayed_score(None, now.isoformat(), now)
    print(f"  score=None → {result:.2f} (expected 0.00)")
    assert result == 0.0

    # None published_at → 0
    result = _time_decayed_score(100, None, now)
    print(f"  published_at=None → {result:.2f} (expected 0.00)")
    assert result == 0.0

    print("  PASS\n")


def test_cosine_similarity():
    """Verify cosine similarity with unit vectors."""
    print("=== Cosine similarity ===")

    # Identical vectors → 1.0
    a = [1.0, 0.0, 0.0]
    result = _cosine_similarity(a, a)
    print(f"  identical → {result:.4f} (expected 1.0000)")
    assert abs(result - 1.0) < 0.001

    # Orthogonal → 0.0
    b = [0.0, 1.0, 0.0]
    result = _cosine_similarity(a, b)
    print(f"  orthogonal → {result:.4f} (expected 0.0000)")
    assert abs(result) < 0.001

    # Opposite → -1.0
    c = [-1.0, 0.0, 0.0]
    result = _cosine_similarity(a, c)
    print(f"  opposite → {result:.4f} (expected -1.0000)")
    assert abs(result - (-1.0)) < 0.001

    # Normalize a 2D vector and check self-similarity
    norm = math.sqrt(3**2 + 4**2)
    d = [3 / norm, 4 / norm]
    result = _cosine_similarity(d, d)
    print(f"  normalized self → {result:.4f} (expected 1.0000)")
    assert abs(result - 1.0) < 0.001

    print("  PASS\n")


def test_dedup():
    """Verify dedup with synthetic embeddings."""
    print("=== Deduplication ===")

    articles = [
        {"id": 1, "title": "Story A", "score": 100},
        {"id": 2, "title": "Story B (dup of A)", "score": 80},
        {"id": 3, "title": "Story C (unique)", "score": 60},
    ]

    # Articles 1 and 2 are near-duplicates (similarity 0.99),
    # article 3 is different
    embeddings = {
        1: [1.0, 0.0, 0.0],
        2: [0.995, 0.0999, 0.0],  # cos sim with [1,0,0] ≈ 0.995
        3: [0.0, 1.0, 0.0],       # orthogonal to both
    }

    result = _deduplicate(articles, embeddings, threshold=0.85)
    kept_ids = [a["id"] for a in result]
    print(f"  Input: 3 articles, kept: {kept_ids}")
    assert kept_ids == [1, 3], f"Expected [1, 3], got {kept_ids}"

    # No embeddings → keep all
    result_no_emb = _deduplicate(articles, {}, threshold=0.85)
    assert len(result_no_emb) == 3, "Should keep all when no embeddings"
    print(f"  No embeddings: kept all {len(result_no_emb)}")

    print("  PASS\n")


# ---------------------------------------------------------------------------
# Live tests (require DB + API keys)
# ---------------------------------------------------------------------------

def test_live_fetch():
    """Fetch recent HN articles from DB."""
    print("=== Live DB fetch ===")
    articles = fetch_hn_articles_recent(hours=48)
    print(f"  Found {len(articles)} HN articles in last 48h")
    if articles:
        top = articles[0]
        print(f"  Top: {top.get('title', '?')[:60]} (score={top.get('score')})")
    print("  PASS\n")
    return articles


def test_live_summary(articles: list[dict] | None = None):
    """Summarize a single article via LLM."""
    print("=== Live LLM summary ===")
    if not articles:
        articles = fetch_hn_articles_recent(hours=48)
    if not articles:
        print("  SKIP: no articles available")
        return

    art = articles[0]
    print(f"  Summarizing: {art.get('title', '?')[:60]}")
    summary = _summarize_article(art)
    print(f"  Summary ({len(summary)} chars):")
    print(f"  {summary[:200]}...")
    print("  PASS\n")


def test_full_digest():
    """Run the full generate_digest() pipeline."""
    print("=== Full digest generation ===")
    stats = generate_digest()
    print(f"  Result: {stats}")
    print("  PASS\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Test digest generation (Phase 5)")
    parser.add_argument("--unit", action="store_true", help="Unit tests only")
    parser.add_argument("--live", action="store_true", help="Live DB/LLM tests only")
    args = parser.parse_args()

    run_unit = not args.live
    run_live = not args.unit

    if run_unit:
        test_time_decay()
        test_cosine_similarity()
        test_dedup()

    if run_live:
        articles = test_live_fetch()
        test_live_summary(articles)
        test_full_digest()

    print("All tests passed.")


if __name__ == "__main__":
    main()
