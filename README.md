# JobRadar

Automated tech-job market intelligence. A Python pipeline pulls postings from
public job APIs every 6 hours, enriches them into structured data, and a Next.js
dashboard surfaces market trends you cannot see by scrolling job boards.

Scope, stated up front: **tech roles only** — engineering, data, design, and
product. A shared title filter enforces this across every source, so the feed
never surprises anyone with sales or accounting jobs.

**Live:** [jobradar.nagysolution.com](https://jobradar.nagysolution.com)

## Architecture

```
GitHub Actions (cron, every 6h)
  └─ Python pipeline
       fetch sources concurrently ──► dedupe (sha256 of company+title+location)
       ──► insert new postings ──► Gemini structured extraction (milestone 2)
       ──► record run metrics
                    │
             Supabase Postgres
                    │
  Next.js dashboard (Vercel) ── read-only via RLS policies
```

Two halves, two languages, one shared schema:

| Half | Stack | Runs on |
| --- | --- | --- |
| Pipeline | Python 3.12, httpx, pydantic, supabase-py | GitHub Actions cron |
| Dashboard | Next.js (App Router), TypeScript, Tailwind | Vercel |

The split is deliberate: Python is the natural language for data fetching and LLM
extraction, TypeScript for the product surface. They never import each other; they
share only the Postgres schema, which is how production pipeline/frontend systems
are actually separated.

## Data sources

All official, public, ToS-clean APIs:

- [Remotive](https://remotive.com) public API
- [Arbeitnow](https://www.arbeitnow.com) job board API (DACH focus)
- [Greenhouse](https://developers.greenhouse.io/job-board.html) public job boards
  for a curated list of well-known tech companies (direct-employer, global roles)
- Milestone 3: Hacker News "Who is hiring" (Algolia), RemoteOK (with attribution), WeWorkRemotely RSS

Each source is one adapter implementing a shared protocol; a failing source never
takes down the run, and per-source health is public on the pipeline page.

## Enrichment

Two layers, so filtering never depends on an LLM being reachable:

1. **Rules (always on, free, instant).** Region, remote policy, seniority, DACH
   fit, and tech-stack tags are derived deterministically from the title,
   location, and description. This alone powers every dashboard filter.
2. **LLM (Gemini 2.5 Flash, opportunistic).** Adds the two things rules do badly:
   a one-line summary and a salary parsed from prose. Bounded per run, backs off
   on rate limits, fully resumable, and skipped entirely if the key is absent so
   the pipeline always completes on heuristic data.

## Repository layout

```
pipeline/            Python pipeline (own pyproject.toml)
  pipeline/
    main.py          entry point: fetch -> dedupe -> store -> enrich -> record run
    models.py        pydantic models + dedupe hash
    db.py            thin Supabase wrapper, no ORM
    enrich_rules.py  deterministic enrichment (region/remote/seniority/stack)
    enrichment.py    Gemini LLM layer (summary + salary), gated + resumable
    sources/         one adapter per job API
src/                 Next.js dashboard (feed + client-side filter/search/sort)
supabase/migrations/ schema as SQL, RLS read-only policies for the public dashboard
.github/workflows/   the cron that runs the pipeline
```

## Running locally

Dashboard:

```bash
npm install
npm run dev
```

Pipeline (no database needed for a dry run):

```bash
cd pipeline
python -m venv .venv && .venv/Scripts/pip install .
.venv/Scripts/python -m pipeline.main --dry-run
```

Copy `.env.example` to `.env.local` and fill in the Supabase and Gemini keys for a
full run.

## Status

- [x] Milestone 1: scaffold + ingestion (dedupe, cron, feed)
- [x] Milestone 2: 3 sources incl. Greenhouse, two-layer enrichment, filter/search/sort UI
- [x] Milestone 3: `/trends` charts, `/pipeline` observability, `/job` raw-vs-extracted detail, tech-only scope filter
- [ ] Remaining: more sources (HN "Who is hiring", RemoteOK, WWR), Python tests, OG image, launch post

Built by [Nandor Nagy](https://github.com/n3ndor). Part of a public portfolio; the
pipeline observability page intentionally shows the machinery instead of hiding it.
