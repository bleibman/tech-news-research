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


# Supabase Postgres connection string (transaction pooler, port 6543).
# Format: postgresql://postgres.PROJECTREF:PASSWORD@aws-0-REGION.pooler.supabase.com:6543/postgres
DATABASE_URL: str = _require("DATABASE_URL")

# Phase 1 ingestion scope (per HN feed). Top + new + best, deduped across feeds.
HN_FEEDS: tuple[str, ...] = ("topstories", "newstories", "beststories")
HN_LIMIT_PER_FEED: int = 60   # cap per feed before dedupe; ~150 unique after overlap
HN_CONCURRENCY: int = 20      # simultaneous item fetches