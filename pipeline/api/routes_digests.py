"""Digest endpoints — browse pre-generated daily digests."""

from __future__ import annotations

import httpx
from fastapi import APIRouter, HTTPException

from src.config import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY

router = APIRouter()

_REST_URL = f"{SUPABASE_URL}/rest/v1"
_HEADERS = {
    "apikey": SUPABASE_SERVICE_ROLE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
}


@router.get("/digests")
async def list_digests(limit: int = 30, offset: int = 0):
    """List recent digests (date + title only, no content_md)."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            f"{_REST_URL}/digests",
            headers={
                **_HEADERS,
                "Range": f"{offset}-{offset + limit - 1}",
                "Prefer": "count=exact",
            },
            params={
                "select": "digest_date,title",
                "order": "digest_date.desc",
            },
        )
        resp.raise_for_status()
    return resp.json()


@router.get("/digests/{date}")
async def get_digest(date: str):
    """Full digest by date (content_md + citations)."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            f"{_REST_URL}/digests",
            headers=_HEADERS,
            params={
                "digest_date": f"eq.{date}",
                "select": "digest_date,title,content_md,citations",
            },
        )
        resp.raise_for_status()

    rows = resp.json()
    if not rows:
        raise HTTPException(status_code=404, detail="Digest not found")
    return rows[0]
