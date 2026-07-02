-- JobRadar initial schema
-- Run in the Supabase SQL editor (or via supabase db push).
-- Writes happen only through the pipeline's secret key (bypasses RLS);
-- the public dashboard reads via the publishable key under read-only policies.

create table sources (
    id          bigint generated always as identity primary key,
    name        text not null unique,
    kind        text not null default 'api',
    last_run_at timestamptz
);

create table postings (
    id            bigint generated always as identity primary key,
    source_id     bigint not null references sources (id),
    external_id   text not null,
    hash          text not null unique,
    company       text not null,
    title         text not null,
    url           text not null,
    location_raw  text not null default '',
    posted_at     timestamptz,
    first_seen_at timestamptz not null default now(),
    raw           jsonb not null default '{}'::jsonb
);

create index postings_source_idx on postings (source_id);
create index postings_first_seen_idx on postings (first_seen_at desc);
create index postings_posted_at_idx on postings (posted_at desc);

create table enrichments (
    posting_id      bigint primary key references postings (id) on delete cascade,
    seniority       text,
    stack           text[] not null default '{}',
    salary_min      integer,
    salary_max      integer,
    salary_currency text,
    remote_policy   text,
    region          text,
    dach_friendly   boolean,
    summary         text,
    model           text,
    tokens          integer,
    enriched_at     timestamptz not null default now(),
    status          text not null default 'ok'
);

create index enrichments_status_idx on enrichments (status);

create table pipeline_runs (
    id           bigint generated always as identity primary key,
    started_at   timestamptz not null,
    finished_at  timestamptz,
    fetched      integer not null default 0,
    new_postings integer not null default 0,
    enriched     integer not null default 0,
    failed       integer not null default 0,
    tokens_used  integer not null default 0,
    duration_s   numeric(8, 2),
    notes        text not null default ''
);

create index pipeline_runs_started_idx on pipeline_runs (started_at desc);

-- Public read-only access for the dashboard (anon/publishable key).
alter table sources enable row level security;
alter table postings enable row level security;
alter table enrichments enable row level security;
alter table pipeline_runs enable row level security;

create policy "public read sources" on sources for select using (true);
create policy "public read postings" on postings for select using (true);
create policy "public read enrichments" on enrichments for select using (true);
create policy "public read pipeline_runs" on pipeline_runs for select using (true);
