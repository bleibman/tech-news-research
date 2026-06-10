"""FastAPI application — serves digest browse and live chat Q&A.

Start locally:
    cd pipeline && uvicorn api.main:app --reload --port 8000
"""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes_digests import router as digests_router
from api.routes_ask import router as ask_router

app = FastAPI(title="Tech News Research API")

# CORS — allow the Next.js frontend origin(s).
_origins_raw = os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000")
_origins = [o.strip() for o in _origins_raw.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(digests_router)
app.include_router(ask_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
