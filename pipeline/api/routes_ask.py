"""Chat endpoint — live Q&A backed by retrieval + synthesis."""

from __future__ import annotations

import asyncio
import traceback

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from api.embed_api import embed_query_api
from src.db import search_chunks
from src.synthesize import synthesize

router = APIRouter()


class AskRequest(BaseModel):
    question: str
    top_k: int = 8


@router.post("/ask")
async def ask(req: AskRequest):
    """Embed question → retrieve chunks → synthesize cited answer."""
    try:
        # Step 1: embed via HF API (async-native)
        query_vec = await embed_query_api(req.question)

        # Step 2: search chunks (sync httpx — run in thread)
        chunks = await asyncio.to_thread(search_chunks, query_vec, req.top_k)

        if not chunks:
            return {
                "answer": "No relevant sources found. The pipeline may not have run yet.",
                "chunks_used": 0,
            }

        # Step 3: synthesize (sync HF client — run in thread)
        answer = await asyncio.to_thread(synthesize, req.question, chunks)

        return {
            "answer": answer,
            "chunks_used": len(chunks),
        }
    except Exception as exc:
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"error": f"{type(exc).__name__}: {exc}"},
        )
