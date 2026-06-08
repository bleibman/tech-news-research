# memory.md — Project Tracking Notes

## Current Status

**Phase:** Phase 2 complete (RSS sources + full-text extraction)
**Branch:** `phase-2`
**Last milestone:** Phase 2 — RSS feeds (Ars Technica, The Verge, TechCrunch) + trafilatura extraction pass.

## What's Done

- [x] Phase 1: HN source, Article model, idempotent upsert (commit `081a0a0`)
- [x] PostgREST switch from psycopg (commit `3e6213d`) — psycopg hangs on Supabase pooler
- [x] First ingestion run — HN articles are in the database
- [x] Phase 2: RSS sources (Ars Technica, The Verge, TechCrunch) via feedparser
- [x] Phase 2: Full-text extraction pass via trafilatura (runs after ingestion)
- [x] Phase 2: Per-source error isolation (one source failing doesn't crash the pipeline)
- [x] Phase 2: DB helpers for extraction (fetch_articles_missing_text, update_article_text)

## Deferred

- **arXiv source** — deferred to a later phase. Hard rate limit (1 req / 3 sec, single connection) makes it a poor fit for the current batch model. Will revisit when the pipeline is more mature.

## What's Next (Phase 3)

1. **Embeddings** — `BAAI/bge-base-en-v1.5` (768-dim), CPU inference via sentence-transformers
2. **chunks table** — `vector(768)` column in Supabase (pgvector)
3. **Chunking strategy** — split raw_text into ~512-token passages
4. **Retrieval** — cosine similarity search over pgvector

## Key Technical Notes

- **DB layer:** Supabase PostgREST via httpx (NOT psycopg — direct Postgres hangs)
- **Supabase project:** `pylevbfvcrmzralattmx`
- **Secrets in:** `pipeline/.env` — `service_role` (Supabase JWT), `hugging_face_token` (not needed until Phase 4)
- **Virtualenv:** `pipeline/.venv` (Python 3.13)
- **Upsert dedupe key:** `(source, external_id)` — makes re-runs idempotent
- **Embedding model (Phase 3):** locked to `BAAI/bge-base-en-v1.5` (768-dim). Changing later = re-embed everything.
- **BGE query prefix:** `"Represent this sentence for searching relevant passages: "` on queries only, NOT on stored documents
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
| 3 | Embeddings + pgvector retrieval (BGE-base, 768-dim) | Planned |
| 4 | LLM synthesis with citation discipline | Planned |
| 5 | Digest generation (Render cron overnight) | Planned |
| 6 | Chat UI (FastAPI + Next.js) | Planned |
| 7 | Agentic web search (chat-only) | Planned |
| 8 | Portfolio polish + README | Planned |

## Session Log

- **2025-06-08:** Read BUILD_PLAN_2.md, confirmed Phase 1 complete with data ingested, created memory.md, starting Phase 2.
- **2026-06-08:** Phase 2 implemented — RSS sources (3 feeds), trafilatura extraction pass, per-source error handling. arXiv deferred.
