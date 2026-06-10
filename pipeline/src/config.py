"""Environment / configuration loading.

Reads .env locally (via python-dotenv); on Render the same vars come from
the service's Environment tab, so load_dotenv() is a harmless no-op there.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv(interpolate=False)  # local .env -> os.environ; no-op if the file isn't present


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"Missing required environment variable: {name}. "
            f"Set it in your .env (local) or the Render service env (deployed)."
        )
    return value


# Supabase PostgREST API (HTTPS, no direct Postgres connection needed).
SUPABASE_URL: str = "https://pylevbfvcrmzralattmx.supabase.co"
SUPABASE_SERVICE_ROLE_KEY: str = _require("service_role")

# Phase 1 ingestion scope (per HN feed). Top + new + best, deduped across feeds.
HN_FEEDS: tuple[str, ...] = ("topstories", "newstories", "beststories")
HN_LIMIT_PER_FEED: int = 60   # cap per feed before dedupe; ~150 unique after overlap
HN_CONCURRENCY: int = 20      # simultaneous item fetches

# Phase 2 — RSS feeds.  Each tuple is (short_name, feed_url).
RSS_FEEDS: list[tuple[str, str]] = [
    ("arstechnica", "https://feeds.arstechnica.com/arstechnica/index"),
    ("theverge", "https://www.theverge.com/rss/index.xml"),
    ("techcrunch", "https://techcrunch.com/feed/"),
]

# Phase 2 — full-text extraction settings.
EXTRACT_CONCURRENCY: int = 5     # polite — hitting real publisher servers
EXTRACT_DELAY: float = 0.5       # seconds between requests per worker
EXTRACT_USER_AGENT: str = (
    "tech-news-research/0.1 (https://github.com/bleibman/tech-news-research; "
    "educational project; polite crawler)"
)

# Phase 3 — embedding + chunking
EMBED_MODEL: str = "BAAI/bge-base-en-v1.5"       # pinned — changing = re-embed everything
EMBED_DIMENSION: int = 768
CHUNK_MAX_TOKENS: int = 480                        # ceiling under BGE's 512 limit
CHUNK_OVERLAP_TOKENS: int = 60
CHUNK_MIN_TOKENS: int = 200                        # don't split anything shorter than this
BGE_QUERY_PREFIX: str = "Represent this sentence for searching relevant passages: "
EMBED_BATCH_SIZE: int = 32                         # sentences per encode() call

# Phase 4 — LLM synthesis (HuggingFace Inference API)
HF_TOKEN: str = os.environ.get("HF_TOKEN", "")     # validated lazily in synthesize.py
SYNTHESIS_MODEL: str = "meta-llama/Llama-3.1-70B-Instruct"
SYNTHESIS_FALLBACK_MODEL: str = "meta-llama/Llama-3.1-8B-Instruct"
SYNTHESIS_MAX_OUTPUT_TOKENS: int = 1024
SYNTHESIS_TOP_K: int = 8
SYNTHESIS_TEMPERATURE: float = 0.1