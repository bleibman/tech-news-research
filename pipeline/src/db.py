"""Storage layer — direct Postgres via psycopg 3.

Phase 1 only writes to `articles`. The upsert is idempotent on the
(source, external_id) unique constraint, so re-running the ingester (which
the overnight cron will do nightly) updates existing rows instead of
duplicating them — score/comment counts refresh, fetched_at bumps.
"""

from __future__ import annotations

import json
from collections.abc import Sequence

import psycopg
from psycopg.rows import dict_row

from .config import DATABASE_URL
from .models import Article

_UPSERT_SQL = """
insert into articles
    (source, external_id, url, title, author, raw_text,
     score, num_comments, published_at, metadata)
values
    (%(source)s, %(external_id)s, %(url)s, %(title)s, %(author)s, %(raw_text)s,
     %(score)s, %(num_comments)s, %(published_at)s, %(metadata)s)
on conflict (source, external_id) do update set
    url          = excluded.url,
    title        = excluded.title,
    author       = excluded.author,
    score        = excluded.score,
    num_comments = excluded.num_comments,
    published_at = excluded.published_at,
    metadata     = excluded.metadata,
    fetched_at   = now()
returning id, (xmax = 0) as inserted;
"""


def get_connection() -> psycopg.Connection:
    """Open a single psycopg connection to Supabase Postgres."""
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


def upsert_articles(articles: Sequence[Article]) -> dict[str, int]:
    """Insert-or-update a batch of Articles. Returns {'inserted', 'updated'}.

    `(xmax = 0)` is the standard Postgres trick to tell whether each row was
    a fresh insert (True) or an update of an existing row (False).
    """
    inserted = updated = 0
    with get_connection() as conn:
        with conn.cursor() as cur:
            for art in articles:
                cur.execute(
                    _UPSERT_SQL,
                    {
                        "source": art.source,
                        "external_id": art.external_id,
                        "url": art.url,
                        "title": art.title,
                        "author": art.author,
                        "raw_text": art.raw_text,
                        "score": art.score,
                        "num_comments": art.num_comments,
                        "published_at": art.published_at,
                        "metadata": json.dumps(art.metadata),
                    },
                )
                row = cur.fetchone()
                if row and row["inserted"]:
                    inserted += 1
                else:
                    updated += 1
        conn.commit()
    return {"inserted": inserted, "updated": updated}