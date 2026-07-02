<div align="center">

# 📡 JobRadar

**Automated tech-job market intelligence.**

A Python pipeline ingests postings from six public job APIs every six hours,
enriches them into structured data, and a Next.js dashboard surfaces market
trends you cannot get by scrolling job boards one listing at a time.

[**▶ Live at jobradar.nagysolution.com**](https://jobradar.nagysolution.com)

![Next.js](https://img.shields.io/badge/Next.js-16-000000?logo=next.js)
![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6?logo=typescript&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![Supabase](https://img.shields.io/badge/Supabase-Postgres-3FCF8E?logo=supabase&logoColor=white)
![Cost](https://img.shields.io/badge/infra%20cost-%240%2Fmonth-3ddc97)

</div>

---

## What it does

Job boards show you one listing at a time. JobRadar aggregates ~1,150 live tech
postings across six sources into one place and answers the questions a single
listing can't:

- **What's actually in demand?** Top technologies, ranked, this month.
- **Where are the roles?** Region split — US, DACH, Europe, APAC, remote-global.
- **How remote is the market really?** Remote / hybrid / onsite shares.
- **What seniority?** Junior through principal distribution.

Every posting is deduplicated across sources, tagged (region, remote policy,
seniority, tech stack), and — where a salary is stated — has it parsed out of the
prose by an LLM. Filter and search the feed, or read the aggregate on `/trends`.

**Scope is stated up front: tech roles only** (engineering, data, design,
product). A shared title filter enforces this across every source, so the feed
never surprises anyone with a sales or accounting listing.

## Architecture

```
 ┌─────────────────────────────────────────────────────────┐
 │  GitHub Actions — cron every 6h                          │
 │                                                          │
 │  Python pipeline (python -m pipeline.main)               │
 │    1. fetch 6 sources concurrently (asyncio.gather)      │
 │    2. tech-role filter + dedupe (sha256 company|title|loc)│
 │    3. insert new postings                                │
 │    4. enrich:  rules layer  (always)                     │
 │                LLM layer    (Groq/Gemini, bounded)       │
 │    5. record run metrics                                 │
 └───────────────────────────┬─────────────────────────────┘
                             │  writes (service key)
                    ┌────────▼────────┐
                    │ Supabase Postgres│
                    └────────┬────────┘
                             │  reads (anon key, RLS read-only)
 ┌───────────────────────────▼─────────────────────────────┐
 │  Next.js dashboard on Vercel                             │
 │    /          filterable feed (search, facets, sort)     │
 │    /trends    aggregate market charts                    │
 │    /pipeline  live observability of the pipeline itself  │
 │    /job/[id]  raw source vs. extracted fields, side by side│
 └──────────────────────────────────────────────────────────┘
```

**Two halves, two languages, one shared schema:**

| Half | Stack | Runs on |
| --- | --- | --- |
| Pipeline | Python 3.12 · httpx · pydantic · supabase-py | GitHub Actions cron |
| Dashboard | Next.js 16 (App Router) · TypeScript · Tailwind 4 | Vercel |

The split is deliberate. Python is the natural language for data ingestion and
LLM work; TypeScript owns the product surface. They never import each other —
they share only the Postgres schema, which is exactly how production
pipeline/frontend systems are separated.

## Engineering decisions worth a look

- **Two-layer enrichment.** Filtering never depends on an LLM being reachable. A
  deterministic rules layer (region, remote policy, seniority, tech-stack tags)
  runs every time, free and instant, and powers every filter. The LLM only adds
  what rules do badly — a prose summary and salary parsing — as an *opportunistic*
  upgrade. ([`enrich_rules.py`](pipeline/pipeline/enrich_rules.py) · [`enrichment.py`](pipeline/pipeline/enrichment.py))
- **Provider-agnostic LLM.** The provider is chosen by whichever key is present
  (Groq or Gemini); adding Claude/OpenAI is one function and a branch. Built after
  Google denied API access on a fresh account — the abstraction turned a hard
  blocker into a config change. ([`providers.py`](pipeline/pipeline/providers.py))
- **Designed for free-tier reality.** LLM enrichment is bounded per run, backs off
  on 429s, and is fully resumable. A run that enriches only part of the backlog is
  a normal, visible state — surfaced on `/pipeline`, not hidden.
- **Independent source failure.** Each source is one adapter behind a shared
  protocol; one API dying never takes down the run, and per-source health is
  public on `/pipeline`.
- **Honest extraction.** `/job/[id]` shows the raw source payload next to the
  extracted fields so anyone can judge quality. Salaries are parsed only when
  stated, never invented.
- **$0/month.** Vercel Hobby, Supabase free tier, GitHub Actions free minutes,
  Groq free tier. No servers, no queues, no paid APIs.

## Data sources

All official, public, ToS-clean APIs — no scraping:

| Source | What it adds |
| --- | --- |
| [Greenhouse](https://developers.greenhouse.io/job-board.html) | Direct-employer roles from curated tech-company boards (Stripe, Anthropic, GitLab, …) |
| [Hacker News](https://news.ycombinator.com) "Who is hiring" | Startup and YC-company roles, parsed from the monthly thread via Algolia |
| [We Work Remotely](https://weworkremotely.com) | Remote-first roles across programming/devops/design/product (RSS) |
| [RemoteOK](https://remoteok.com) | Remote roles (attribution honored in the UI) |
| [Remotive](https://remotive.com) | Curated remote listings |
| [Arbeitnow](https://www.arbeitnow.com) | DACH-market coverage |

## Repository layout

```
pipeline/                    Python pipeline (its own pyproject.toml)
  pipeline/
    main.py                  entry: fetch → filter → dedupe → store → enrich → record
    models.py                pydantic models + dedupe hash
    db.py                    thin Supabase wrapper, no ORM
    tech_filter.py           the single "is this a tech role?" definition
    enrich_rules.py          deterministic enrichment (region/remote/seniority/stack)
    enrichment.py            LLM layer (summary + salary), gated + resumable
    providers.py             swappable LLM providers (Groq / Gemini)
    sources/                 one adapter per job API (6)
src/                         Next.js dashboard
  app/                       feed, /trends, /pipeline, /job/[id], OG image
  components/FeedExplorer    client-side search / faceted filters / sort
  lib/                       supabase client, types, formatting
supabase/migrations/         schema as SQL + RLS read-only policies
.github/workflows/           the cron that runs the pipeline
```

## Running locally

**Dashboard:**

```bash
npm install
npm run dev
```

**Pipeline** (no database or keys needed for a dry run — it fetches, filters, and
dedupes in memory, then prints a summary):

```bash
cd pipeline
python -m venv .venv && .venv/Scripts/pip install .
.venv/Scripts/python -m pipeline.main --dry-run
```

Copy `.env.example` to `.env.local` and fill in the Supabase (and optional LLM)
keys for a full run that writes to the database.

## Status

- [x] Ingestion: 6 sources, tech-role filter, cross-source dedupe, cron
- [x] Enrichment: deterministic rules + provider-agnostic LLM (Groq/Gemini)
- [x] Dashboard: filterable feed, `/trends`, `/pipeline`, `/job/[id]`, OG image
- [ ] Next: Python test suite, email digest opt-in, more curated boards

---

<div align="center">

Built by [**Nandor Nagy**](https://github.com/n3ndor) · part of a public portfolio.<br>
The pipeline observability page intentionally shows the machinery instead of hiding it.

</div>
