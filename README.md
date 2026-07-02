# JobRadar

Automated job-market intelligence. A Python pipeline pulls remote job postings from
public APIs every 6 hours, enriches them with an LLM into structured data, and a
Next.js dashboard surfaces market trends you cannot see by scrolling job boards.

**Live:** _coming soon at jobradar.nagysolution.com_

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
- Milestone 3: Hacker News "Who is hiring" (Algolia), RemoteOK (with attribution), WeWorkRemotely RSS

Each source is one adapter implementing a shared protocol; a failing source never
takes down the run, and per-source health is public on the pipeline page.

## Repository layout

```
pipeline/            Python pipeline (own pyproject.toml)
  pipeline/
    main.py          entry point: fetch -> dedupe -> store -> record run
    models.py        pydantic models + dedupe hash
    db.py            thin Supabase wrapper, no ORM
    sources/         one adapter per job API
src/                 Next.js dashboard
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

- [x] Milestone 1: scaffold + ingestion (2 sources, dedupe, cron, bare feed)
- [ ] Milestone 2: Gemini enrichment, filters, job detail, pipeline observability page
- [ ] Milestone 3: trends charts, remaining sources, tests, polish, launch

Built by [Nandor Nagy](https://github.com/n3ndor). Part of a public portfolio; the
pipeline observability page intentionally shows the machinery instead of hiding it.
