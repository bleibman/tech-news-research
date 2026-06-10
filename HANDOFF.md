# Session Handoff — Tech News Research App

## Project Location
`/Users/brandonleibman/Desktop/tech-news-research`

## Build Plan
Full build plan is at `/Users/brandonleibman/Downloads/BUILD_PLAN_2.md` — read it first.

## Current State

### Phase 1 — COMPLETE (committed + pushed)
- Branch `main` has the Phase 1 commit: `081a0a0`
- Branch `build` was created for ongoing work (currently checked out)
- HackerNews source, Article model, idempotent upsert, pluggable Source protocol all built

### What Changed This Session (on `build` branch, NOT yet committed)

**Switched from psycopg (direct Postgres) to PostgREST via httpx.**

The `psycopg` connection to Supabase hangs indefinitely — TCP connects but the Postgres protocol handshake never completes. Root cause unclear (not SSL, not IPv6, not paused project — Supabase SQL Editor works fine in browser). We switched `db.py` to use Supabase's PostgREST REST API over HTTPS instead.

Files changed on `build` branch:
1. **`pipeline/src/config.py`** — Replaced `DATABASE_URL` with `SUPABASE_URL` (hardcoded project URL) and `SUPABASE_SERVICE_ROLE_KEY` (from env var `service_role`)
2. **`pipeline/src/db.py`** — Complete rewrite: uses `httpx.post()` to Supabase PostgREST API with `Prefer: resolution=merge-duplicates` for upsert behavior. No more psycopg.
3. **`pipeline/src/run_ingest.py`** — Updated print statement: `stats['upserted']` instead of `stats['inserted']`/`stats['updated']` (PostgREST doesn't distinguish)
4. **`pipeline/test_db.py`** — Rewritten to test PostgREST GET on articles table
5. **`pipeline/requirements.txt`** — Removed `psycopg[binary]`, added comment that PostgREST via httpx is used instead

### What has NOT been tested yet
- **The PostgREST connection has not been verified.** The Bash tool in this session had persistent issues running Python (output never flushed). The user needs to run `python3 test_db.py` from their terminal to confirm the REST API works.
- **The ingestion has never been run.** Phase 1 code is complete but `python -m src.run_ingest` has not executed successfully yet.

## Immediate Next Steps (in order)

1. **Test the PostgREST connection:**
   ```
   cd ~/Desktop/tech-news-research/pipeline && source venv/bin/activate && python3 test_db.py
   ```
   Expected output: `Status: 200` and a JSON body (empty array `[]` is fine — table has no rows yet).

2. **Run the first ingestion:**
   ```
   cd ~/Desktop/tech-news-research/pipeline && source venv/bin/activate && python3 -m src.run_ingest
   ```
   Expected: fetches ~150 HN articles, upserts them via PostgREST.

3. **Commit the `build` branch changes** once ingestion succeeds.

4. **Begin Phase 2** — RSS sources + trafilatura full-text extraction (see BUILD_PLAN_2.md).

## Environment Details

- **Venv:** `pipeline/venv` (also a `.venv` exists — use `venv`)
- **Python:** 3.13
- **Git remote:** `https://github.com/bleibman/tech-news-research.git` (SSH also configured: `git@github.com:bleibman/tech-news-research.git`)
- **Supabase project ref:** `pylevbfvcrmzralattmx`
- **Supabase URL:** `https://pylevbfvcrmzralattmx.supabase.co`
- **Secrets in:** `pipeline/.env` (never committed — `.gitignore` excludes it)
  - `service_role` — Supabase service role JWT (used for PostgREST auth)
  - `hugging_face_token` — HF token (not needed until Phase 4)
  - `DATABASE_URL` — still in .env but no longer used by code

## Known Issues
- **Bash tool output buffering:** Python commands run via Claude's Bash tool in this session consistently produced no stdout. Commands ran but output never flushed. Running commands directly in the user's terminal works fine.
- **psycopg connection:** Hangs on Supabase pooler (both old `aws-1-us-east-1.pooler.supabase.com:6543` and new `db.pylevbfvcrmzralattmx.supabase.co:6543`). TCP connects, Postgres handshake never completes. If this needs to be revisited later (e.g., for pgvector in Phase 3), may need to debug further or use Supabase's direct connection on port 5432.
