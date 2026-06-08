# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Tech news RAG (Retrieval-Augmented Generation) research tool that ingests articles from multiple sources, embeds them, and serves both a pre-generated morning digest and live Q&A — "one engine, two front doors." Currently in early phases (ingestion built, extraction/embedding/synthesis ahead).

## Commands

All commands run from `pipeline/`:

```bash
source .venv/bin/activate              # Python 3.13 virtualenv
python3 -m src.run_ingest              # Run full ingestion pipeline
python3 test_db.py                     # Quick PostgREST connectivity check
pip install -r requirements.txt        # Install dependencies
```

No test framework, linter, or build system is configured yet.

## Architecture

### Ingestion Pipeline (`pipeline/src/`)

Entry point is `run_ingest.py` which iterates over registered `SOURCES`, calls `await source.fetch()` on each, then batch-upserts the collected `Article` objects to Supabase.

**Source protocol** (`sources/base.py`): Any class with a `name: str` attribute and `async fetch() -> list[Article]` method. New sources drop into the `SOURCES` list in `run_ingest.py` without touching existing code. Currently only `HackerNewsSource`.

**Article model** (`models.py`): Single dataclass that every source normalizes into. Maps 1:1 to the `articles` table. The `(source, external_id)` pair is the dedupe key matching the DB unique constraint.

**DB layer** (`db.py`): Uses Supabase PostgREST API over HTTPS (not direct Postgres — psycopg hangs on Supabase's pooler). Upserts use `Prefer: resolution=merge-duplicates` header. This makes ingestion runs idempotent and safe to repeat.

**Config** (`config.py`): Loads `.env` via python-dotenv. The `service_role` env var is required (Supabase service role JWT). Supabase project URL is hardcoded.

### Database (Supabase)

- **`articles` table**: unique constraint on `(source, external_id)`, columns match `Article` dataclass fields plus auto `fetched_at`
- **Future**: `chunks` table with `vector(768)` column (pgvector, Phase 3), `digests` table (Phase 5)
- Schema is managed via Supabase dashboard SQL Editor, not migration files in this repo

### Planned Architecture (BUILD_PLAN_2.md)

Phases build incrementally: HN ingestion (done) → RSS + full-text extraction → embeddings + retrieval → LLM synthesis → digest generation (Render cron) → chat UI (FastAPI + Next.js) → agentic web search.

Heavy work runs overnight and writes finished digests to DB. The morning browse reads pre-generated content. The chat path reuses retrieval + synthesis with on-demand LLM calls.

## Key Design Decisions

- **PostgREST over psycopg**: Direct Postgres connection hangs on Supabase pooler (TCP connects, protocol handshake never completes). PostgREST via httpx works reliably.
- **Idempotent upserts**: The nightly cron model depends on safe re-runs. Partial failures self-heal next run. HN scores refresh on re-ingest.
- **Per-source failure isolation**: One source failing must not crash the pipeline. Wrap each `fetch()` so failures log and yield empty lists.
- **Embedding model locked to `BAAI/bge-base-en-v1.5` (768-dim)**: Changing model or dimension later means re-embedding everything + altering the column. BGE requires query prefix `"Represent this sentence for searching relevant passages: "` but no prefix on stored documents.
- **CPU embeddings, not HF API**: Free and sufficient for overnight batch where latency doesn't matter.
- **Source quality > model quality**: ~80% of output quality comes from sources + retrieval, not the synthesis model.

## Environment

- **Python**: 3.13
- **Virtualenv**: `pipeline/.venv`
- **Secrets**: `pipeline/.env` (never committed). Required: `service_role` (Supabase JWT). Future: `hugging_face_token`.
- **Supabase project**: `pylevbfvcrmzralattmx`
- **Git remote**: `https://github.com/bleibman/tech-news-research.git`
