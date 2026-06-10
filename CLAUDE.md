# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Tech news RAG (Retrieval-Augmented Generation) research tool that ingests articles from multiple sources, embeds them, and serves both a pre-generated morning digest and live Q&A — "one engine, two front doors." Phases 1–6 complete: ingestion, extraction, embeddings, synthesis, digest generation, and chat interface.

## Commands

Pipeline commands run from `pipeline/`:

```bash
source .venv/bin/activate              # Python 3.13 virtualenv
python3 -m src.run_ingest              # Run full ingestion pipeline
python3 test_db.py                     # Quick PostgREST connectivity check
pip install -r requirements.txt        # Install dependencies
uvicorn api.main:app --reload --port 8000  # Start FastAPI dev server
```

Frontend commands run from `frontend/`:

```bash
npm install                            # Install dependencies
npm run dev                            # Start Next.js dev server (port 3000)
npm run build                          # Production build
```

No test framework or linter is configured yet.

## Architecture

### Ingestion Pipeline (`pipeline/src/`)

Entry point is `run_ingest.py` which iterates over registered `SOURCES`, calls `await source.fetch()` on each, then batch-upserts the collected `Article` objects to Supabase.

**Source protocol** (`sources/base.py`): Any class with a `name: str` attribute and `async fetch() -> list[Article]` method. New sources drop into the `SOURCES` list in `run_ingest.py` without touching existing code. Currently only `HackerNewsSource`.

**Article model** (`models.py`): Single dataclass that every source normalizes into. Maps 1:1 to the `articles` table. The `(source, external_id)` pair is the dedupe key matching the DB unique constraint.

**DB layer** (`db.py`): Uses Supabase PostgREST API over HTTPS (not direct Postgres — psycopg hangs on Supabase's pooler). Upserts use `Prefer: resolution=merge-duplicates` header. This makes ingestion runs idempotent and safe to repeat.

**Config** (`config.py`): Loads `.env` via python-dotenv. The `service_role` env var is required (Supabase service role JWT). Supabase project URL is hardcoded.

### FastAPI Web Service (`pipeline/api/`)

Serves two "front doors" to the same RAG engine:

- **`/digests`** — Browse pre-generated daily digests (server-rendered in Next.js)
- **`/ask`** — Live Q&A: embed query → retrieve chunks → synthesize cited answer

**Key design**: Uses HF Inference API for query embedding (`embed_api.py`) instead of local sentence-transformers, keeping RAM under 512 MB for Render's cheap tier. The overnight cron job continues using the CPU model.

**`main.py`**: FastAPI app with CORS middleware. Origins from `ALLOWED_ORIGINS` env var.
**`routes_digests.py`**: `GET /digests` (list) and `GET /digests/{date}` (full content) via PostgREST.
**`routes_ask.py`**: `POST /ask` — async embed → threaded search + synthesize. Reuses `src.synthesize.synthesize()`.
**`embed_api.py`**: `embed_query_api()` — async HF Inference API call for BGE query embeddings.

### Next.js Frontend (`frontend/`)

App Router, TypeScript, Tailwind CSS. Three routes:

- `/` — Landing page with links to digest and chat
- `/digest` — List of recent digests (server component)
- `/digest/[date]` — Single digest rendered as markdown
- `/chat` — Interactive Q&A (client component)

Communicates with FastAPI via `NEXT_PUBLIC_API_URL` env var.

### Database (Supabase)

- **`articles` table**: unique constraint on `(source, external_id)`, columns match `Article` dataclass fields plus auto `fetched_at`
- **`chunks` table**: `vector(768)` column (pgvector), linked to articles
- **`digests` table**: keyed by `digest_date`, stores `content_md` and `citations`
- Schema is managed via Supabase dashboard SQL Editor, not migration files in this repo

### Architecture Overview

Heavy work runs overnight (Render cron): ingest → extract → embed → generate digest. The morning browse reads pre-generated digests. The chat path reuses retrieval + synthesis with on-demand LLM calls via the FastAPI service.

## Key Design Decisions

- **PostgREST over psycopg**: Direct Postgres connection hangs on Supabase pooler (TCP connects, protocol handshake never completes). PostgREST via httpx works reliably.
- **Idempotent upserts**: The nightly cron model depends on safe re-runs. Partial failures self-heal next run. HN scores refresh on re-ingest.
- **Per-source failure isolation**: One source failing must not crash the pipeline. Wrap each `fetch()` so failures log and yield empty lists.
- **Embedding model locked to `BAAI/bge-base-en-v1.5` (768-dim)**: Changing model or dimension later means re-embedding everything + altering the column. BGE requires query prefix `"Represent this sentence for searching relevant passages: "` but no prefix on stored documents.
- **CPU embeddings for batch, HF API for live queries**: Overnight cron uses local sentence-transformers (free, no RAM pressure). The FastAPI web service uses HF Inference API to stay under 512 MB RAM on Render's cheap tier.
- **Source quality > model quality**: ~80% of output quality comes from sources + retrieval, not the synthesis model.

## Environment

- **Python**: 3.13
- **Virtualenv**: `pipeline/.venv`
- **Secrets**: `pipeline/.env` (never committed). Required: `service_role` (Supabase JWT), `HF_TOKEN` (HuggingFace Inference API).
- **Supabase project**: `pylevbfvcrmzralattmx`
- **Git remote**: `https://github.com/bleibman/tech-news-research.git`
- **FastAPI (Render)**: Web service at `pipeline/`, start: `uvicorn api.main:app --host 0.0.0.0 --port $PORT`. Env vars: `service_role`, `HF_TOKEN`, `ALLOWED_ORIGINS`.
- **Next.js (Vercel)**: Frontend at `frontend/`. Env var: `NEXT_PUBLIC_API_URL` (FastAPI URL).

## Git Corruption Recovery

If git operations fail with SIGBUS (signal 10) or `pack-objects died` errors, the `.git` object database has corrupted objects (likely from filesystem-level issues). Do NOT attempt `git repack`, `git format-patch`, or `git gc` on the corrupted repo — `pack-objects` walks the full history graph and will crash on any corrupt ancestor.

**Fix procedure:**
1. `git clone <remote-url> /tmp/tech-news-fresh` — fresh clone from GitHub
2. `rsync -av --exclude='.git' ./ /tmp/tech-news-fresh/` — copy working tree into fresh clone
3. `cd /tmp/tech-news-fresh && git add -A && git commit && git push origin main` — commit and push
4. Back in original repo: `rm -rf .git && cp -R /tmp/tech-news-fresh/.git .` — replace corrupted .git
5. `git fsck --full && git gc --prune=now` — verify integrity
6. `rm -rf /tmp/tech-news-fresh` — clean up
