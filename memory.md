# memory.md — Project Tracking Notes

## Current Status

**Phase:** Phase 3 complete (embeddings + chunking + semantic retrieval)
**Branch:** merging `phase-3` → `main`
**Last milestone:** Phase 3 — BGE embeddings, token-aware chunking, pgvector retrieval. 459 articles embedded.

## What's Done

- [x] Phase 1: HN source, Article model, idempotent upsert (commit `081a0a0`)
- [x] PostgREST switch from psycopg (commit `3e6213d`) — psycopg hangs on Supabase pooler
- [x] First ingestion run — HN articles are in the database
- [x] Phase 2: RSS sources (Ars Technica, The Verge, TechCrunch) via feedparser
- [x] Phase 2: Full-text extraction pass via trafilatura (runs after ingestion)
- [x] Phase 2: Per-source error isolation (one source failing doesn't crash the pipeline)
- [x] Phase 2: DB helpers for extraction (fetch_articles_missing_text, update_article_text)

- [x] Phase 3: Token-aware chunking (paragraph → sentence → word boundaries, 480-token ceiling, 60-token overlap)
- [x] Phase 3: BGE-base embeddings via sentence-transformers (CPU, lazy-loaded singleton)
- [x] Phase 3: chunks table in Supabase with pgvector (768-dim), match_chunks RPC for cosine similarity search
- [x] Phase 3: Embedding pass integrated into run_ingest.py (chunk → embed → insert, idempotent via already-embedded check)
- [x] Phase 3: Semantic retrieval tested end-to-end (test_retrieval.py)
- [x] Phase 3: Fixed infinite loop bug in chunk_text overlap logic

## Deferred

- **arXiv source** — deferred to a later phase. Hard rate limit (1 req / 3 sec, single connection) makes it a poor fit for the current batch model. Will revisit when the pipeline is more mature.
- **Render cron job** — deferred until synthesis/digest is working. No point running a nightly cron until the pipeline produces something consumable.

## What's Next (Phase 4)

1. **LLM synthesis** — Claude API for generating answers from retrieved chunks
2. **Citation discipline** — responses must cite source articles
3. **Retrieval + synthesis pipeline** — query → embed → search → synthesize with citations

## Key Technical Notes

- **DB layer:** Supabase PostgREST via httpx (NOT psycopg — direct Postgres hangs)
- **Supabase project:** `pylevbfvcrmzralattmx`
- **Secrets in:** `pipeline/.env` — `service_role` (Supabase JWT), `hugging_face_token` (not needed until Phase 4)
- **Virtualenv:** `pipeline/.venv` (Python 3.13)
- **Upsert dedupe key:** `(source, external_id)` — makes re-runs idempotent
- **Embedding model:** locked to `BAAI/bge-base-en-v1.5` (768-dim). Changing later = re-embed everything.
- **BGE query prefix:** `"Represent this sentence for searching relevant passages: "` on queries only, NOT on stored documents
- **Chunking:** 480-token ceiling, 60-token overlap, paragraph → sentence → word split hierarchy
- **Chunks DB:** `chunks` table with `vector(768)`, `match_chunks` RPC for cosine similarity search
- **Build plan location:** `/Users/brandonleibman/Downloads/BUILD_PLAN_2.md`
- **Extraction:** trafilatura for body text, httpx for fetching. Best-effort — failures are logged and skipped.
- **Politeness:** 5 concurrent extractors, 0.5s delay between requests, descriptive User-Agent.

## Architecture Reminders

- **"One engine, two front doors"** — digest (pre-generated overnight) and chat (live Q&A) share retrieval + synthesis code
- **Source protocol:** any class with `name: str` + `async fetch() -> list[Article]` — drop into `SOURCES` list in `run_ingest.py`
- **Per-source failure isolation:** each `fetch()` is wrapped in try/except so one source failing doesn't crash the run
- **Extraction runs AFTER ingestion** as a separate pass, not inside each source
- **Source quality > model quality** — ~80% of output quality comes from sources + retrieval

## Phase Roadmap (quick reference)

| Phase | What | Status |
|-------|------|--------|
| 1 | HN ingestion + Article model + upsert | Done |
| 2 | RSS sources + trafilatura extraction | Done |
| 3 | Embeddings + pgvector retrieval (BGE-base, 768-dim) | Done |
| 4 | LLM synthesis with citation discipline | Planned |
| 5 | Digest generation (Render cron overnight) | Planned |
| 6 | Chat UI (FastAPI + Next.js) | Planned |
| 7 | Agentic web search (chat-only) | Planned |
| 8 | Portfolio polish + README | Planned |

## Session Log

- **2025-06-08:** Read BUILD_PLAN_2.md, confirmed Phase 1 complete with data ingested, created memory.md, starting Phase 2.
- **2026-06-08:** Phase 2 implemented — RSS sources (3 feeds), trafilatura extraction pass, per-source error handling. arXiv deferred.
- **2026-06-09:** Phase 3 implemented — token-aware chunking, BGE embeddings, pgvector retrieval. Fixed infinite loop in chunk overlap logic. Full pipeline run: 459 articles embedded, semantic search verified.
