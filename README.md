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
![Tests](https://img.shields.io/badge/tests-56%2B13%20passing-3ddc97)
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
seniority, tech stack), AI-summarized, and — where a salary is stated — has it
parsed out of the prose. Filter and search the feed, or read the aggregate on
`/trends`. **Every filtered search is a shareable URL**: bookmark "senior Python,
remote, salary stated" and open it pre-applied every morning, or send it to
someone as a link.

**Scope is stated up front: tech roles only** (engineering, data, design,
product). A shared title filter enforces this across every source, so the feed
never surprises anyone with a sales or accounting listing.

## The AI layer (read this part)

Most of the pipeline is deliberately deterministic — but three things are only
possible because an LLM reads every posting's **full description**, and they are
the difference between this and a feed aggregator:

1. **One-line summaries.** Walls of recruiter prose become a single neutral
   sentence on every card, tagged `AI` in the UI.
2. **Salaries parsed out of prose.** "80–95k EUR depending on experience" buried
   in paragraph four becomes structured `salary_min/max/currency`, filterable.
   Never invented: postings without a stated salary stay empty, and the numbers
   show how rare published salaries really are.
3. **A lie detector for remote tags.** Job boards flag postings as "remote" while
   the description says *"an unseren Standorten"* or *"Available Locations:
   Munich"*. Rules can't catch that (they only see the location field); the LLM
   reads the whole text and overrides wrong remote/region tags with what the
   posting actually says. Real example from production: a "Global / Remote"
   posting corrected to *hybrid, DACH* — wrong tag, and the correction made it
   more relevant, not less.

All of it costs almost nothing extra: the description is already sent for the
summary, so verifying tags adds ~30 output tokens per posting. The LLM is also
never a dependency — if the key is missing or rate-limited, the pipeline
completes on the deterministic layer and catches up later, visibly, on
[`/pipeline`](https://jobradar.nagysolution.com/pipeline).

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
- **The ingestion layer is my own open-source package.** The six source
  adapters were extracted into [**jobfeeds**](https://github.com/n3ndor/jobfeeds)
  (`pip install jobfeeds`) and this pipeline now depends on it like any other
  consumer. What stays in this repo is product policy (which Greenhouse
  boards, the tech-role filter); feed access is the package's job. Extracting
  a real library from a working system, then dogfooding it, was the point.
- **Independent source failure.** Each source is one adapter behind a shared
  protocol (jobfeeds' `fetch_all`); one API dying never takes down the run,
  and per-source health is public on `/pipeline`.
- **Honest extraction.** `/job/[id]` shows the raw source payload next to the
  extracted fields so anyone can judge quality. Salaries are parsed only when
  stated, never invented.
- **Search state lives in the URL.** Filters survive the back button, and every
  search is shareable/bookmarkable. Synced via `history.replaceState`, so typing
  costs zero server round-trips.
- **Always-fresh pages.** Data pages render per request instead of ISR: on a
  low-traffic site, revalidation-based caching serves stale snapshots to nearly
  every visitor. A ~200ms live read beats a cached lie.

## Runs entirely on free tiers ($0/month)

No servers, no queues, no paid APIs, no credit card anywhere in the stack:

| Service | Free tier used for |
| --- | --- |
| GitHub Actions | the 6-hourly pipeline cron + CI test runs (~10 min/day of the 2,000 free min/month) |
| Supabase | Postgres + row-level security, thousands of rows |
| Vercel Hobby | Next.js hosting, per-request server rendering, OG image generation |
| Groq | LLM enrichment (bounded per run, backs off on rate limits, resumes next run) |

The free-tier constraint is treated as a design input, not a limitation to
apologize for: bounded batches, resumable backfills, and per-source failure
isolation exist *because* the budget is zero.

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
    enrichment.py            LLM layer (summary + salary + tag verification), gated + resumable
    providers.py             swappable LLM providers (Groq / Gemini)
    sources.py               source configuration; adapters live in the
                             jobfeeds package (github.com/n3ndor/jobfeeds)
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

- [x] Ingestion: 6 sources via the jobfeeds package, tech-role filter, cross-source dedupe, cron
- [x] Enrichment: deterministic rules + provider-agnostic LLM (Groq/Gemini)
- [x] AI tag verification: LLM corrects remote/region tags against the full description
- [x] Dashboard: filterable feed with shareable search URLs, `/trends`, `/pipeline`, `/job/[id]`, OG image
- [x] Test suite: 56 pipeline tests here + 13 adapter tests in the jobfeeds package (all HTTP mocked with respx), run in CI

**On the radar:** email digest · salary benchmarks by stack & region · company
hiring velocity · ghost-job detector (postings reposted for months) · public API

---

<div align="center">

Built by [**Nandor Nagy**](https://github.com/n3ndor) · part of a public portfolio.<br>
The pipeline observability page intentionally shows the machinery instead of hiding it.

</div>
