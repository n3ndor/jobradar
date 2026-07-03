"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import type { Posting } from "@/lib/types";
import { formatSalary, relativeTime } from "@/lib/format";

const RENDER_CAP = 250;

type Sort = "newest" | "oldest";

function unique(values: (string | null | undefined)[]): string[] {
  return [...new Set(values.filter((v): v is string => !!v))];
}

function toggle(set: Set<string>, value: string): Set<string> {
  const next = new Set(set);
  if (next.has(value)) next.delete(value);
  else next.add(value);
  return next;
}

const REMOTE_ORDER = ["remote", "hybrid", "onsite", "unknown"];
const SENIORITY_ORDER = ["junior", "mid", "senior", "lead", "principal"];

function ChipGroup({
  legend,
  options,
  selected,
  onToggle,
}: {
  legend: string;
  options: { value: string; label: string; count: number }[];
  selected: Set<string>;
  onToggle: (value: string) => void;
}) {
  const [open, setOpen] = useState(false);
  if (options.length === 0) return null;
  // Collapsed groups still show their selected chips, so an active filter is
  // always visible (and removable) without opening the group.
  const shown = open ? options : options.filter((opt) => selected.has(opt.value));
  return (
    <fieldset className="min-w-0">
      <legend className="w-full">
        <button
          type="button"
          aria-expanded={open}
          onClick={() => setOpen((o) => !o)}
          className="flex w-full items-center gap-1.5 rounded py-0.5 font-mono text-[11px] uppercase tracking-wider text-faint transition-colors hover:text-muted"
        >
          <svg
            viewBox="0 0 16 16"
            aria-hidden="true"
            className={
              "size-3 shrink-0 transition-transform " + (open ? "rotate-90" : "")
            }
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <path d="M6 4l4 4-4 4" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          {legend}
          {selected.size > 0 && (
            <span className="rounded-full border border-accent/40 bg-accent/15 px-1.5 text-[10px] normal-case text-accent">
              {selected.size}
            </span>
          )}
        </button>
      </legend>
      {shown.length > 0 && (
        <div className="mt-1.5 flex flex-wrap gap-1.5">
          {shown.map((opt) => {
            const active = selected.has(opt.value);
            return (
              <button
                key={opt.value}
                type="button"
                aria-pressed={active}
                onClick={() => onToggle(opt.value)}
                className={
                  "rounded-full border px-2.5 py-1 text-xs transition-colors " +
                  (active
                    ? "border-accent bg-accent/15 text-accent"
                    : "border-border bg-surface text-muted hover:border-border-strong hover:text-foreground")
                }
              >
                {opt.label}
                <span className="ml-1 text-[10px] text-faint">{opt.count}</span>
              </button>
            );
          })}
        </div>
      )}
    </fieldset>
  );
}

export function FeedExplorer({ postings }: { postings: Posting[] }) {
  // Filter state lives in the URL so it survives back navigation and makes
  // searches shareable. The page is rendered dynamically, so the server sees
  // the same params and the initial render matches on hydration.
  const params = useSearchParams();
  const fromParam = (key: string) =>
    new Set((params.get(key) ?? "").split(",").filter(Boolean));

  const [search, setSearch] = useState(params.get("q") ?? "");
  const [regions, setRegions] = useState<Set<string>>(() => fromParam("region"));
  const [remotes, setRemotes] = useState<Set<string>>(() => fromParam("remote"));
  const [seniorities, setSeniorities] = useState<Set<string>>(() => fromParam("seniority"));
  const [sources, setSources] = useState<Set<string>>(() => fromParam("source"));
  const [stacks, setStacks] = useState<Set<string>>(() => fromParam("stack"));
  const [dachOnly, setDachOnly] = useState(params.get("dach") === "1");
  const [salaryOnly, setSalaryOnly] = useState(params.get("salary") === "1");
  const [sort, setSort] = useState<Sort>(params.get("sort") === "oldest" ? "oldest" : "newest");

  useEffect(() => {
    const next = new URLSearchParams();
    if (search) next.set("q", search);
    for (const [key, set] of [
      ["region", regions],
      ["remote", remotes],
      ["seniority", seniorities],
      ["source", sources],
      ["stack", stacks],
    ] as const) {
      if (set.size) next.set(key, [...set].join(","));
    }
    if (dachOnly) next.set("dach", "1");
    if (salaryOnly) next.set("salary", "1");
    if (sort !== "newest") next.set("sort", sort);
    const qs = next.toString();
    // replaceState instead of router.replace: updates the URL without a server
    // round-trip, and Next keeps useSearchParams in sync.
    window.history.replaceState(null, "", qs ? `?${qs}` : window.location.pathname);
  }, [search, regions, remotes, seniorities, sources, stacks, dachOnly, salaryOnly, sort]);

  const facets = useMemo(() => {
    const count = (fn: (p: Posting) => string | null | undefined) => {
      const m = new Map<string, number>();
      for (const p of postings) {
        const v = fn(p);
        if (v) m.set(v, (m.get(v) ?? 0) + 1);
      }
      return m;
    };
    const byOrder = (m: Map<string, number>, order: string[]) =>
      unique([...order, ...m.keys()])
        .filter((k) => m.has(k))
        .map((value) => ({ value, label: value, count: m.get(value)! }));
    const bySize = (m: Map<string, number>) =>
      [...m.entries()]
        .sort((a, b) => b[1] - a[1])
        .map(([value, c]) => ({ value, label: value, count: c }));

    const stackCounts = new Map<string, number>();
    for (const p of postings) {
      for (const s of p.enrichments?.stack ?? []) {
        stackCounts.set(s, (stackCounts.get(s) ?? 0) + 1);
      }
    }

    return {
      region: bySize(count((p) => p.enrichments?.region)),
      remote: byOrder(count((p) => p.enrichments?.remote_policy), REMOTE_ORDER),
      seniority: byOrder(count((p) => p.enrichments?.seniority), SENIORITY_ORDER),
      source: bySize(count((p) => p.sources?.name)),
      stack: [...stackCounts.entries()]
        .sort((a, b) => b[1] - a[1])
        .slice(0, 18)
        .map(([value, c]) => ({ value, label: value, count: c })),
    };
  }, [postings]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    const result = postings.filter((p) => {
      const e = p.enrichments;
      if (q && !p.title.toLowerCase().includes(q) && !p.company.toLowerCase().includes(q))
        return false;
      if (regions.size && !(e?.region && regions.has(e.region))) return false;
      if (remotes.size && !(e?.remote_policy && remotes.has(e.remote_policy))) return false;
      if (seniorities.size && !(e?.seniority && seniorities.has(e.seniority))) return false;
      if (sources.size && !(p.sources?.name && sources.has(p.sources.name))) return false;
      if (stacks.size) {
        const ps = e?.stack ?? [];
        if (!ps.some((s) => stacks.has(s))) return false;
      }
      if (dachOnly && !e?.dach_friendly) return false;
      if (salaryOnly && e?.salary_min == null && e?.salary_max == null) return false;
      return true;
    });
    result.sort((a, b) => {
      const cmp = Date.parse(a.first_seen_at) - Date.parse(b.first_seen_at);
      return sort === "newest" ? -cmp : cmp;
    });
    return result;
  }, [postings, search, regions, remotes, seniorities, sources, stacks, dachOnly, salaryOnly, sort]);

  const activeCount =
    regions.size + remotes.size + seniorities.size + sources.size + stacks.size +
    (dachOnly ? 1 : 0) + (salaryOnly ? 1 : 0);

  const clearAll = () => {
    setSearch("");
    setRegions(new Set());
    setRemotes(new Set());
    setSeniorities(new Set());
    setSources(new Set());
    setStacks(new Set());
    setDachOnly(false);
    setSalaryOnly(false);
  };

  return (
    // Portal layout at md+: the grid is viewport-bounded and the two columns
    // scroll independently, so the page itself stays short and the footer is
    // always within reach. Mobile keeps natural document scrolling.
    <div className="grid gap-6 md:h-[calc(100dvh-20.5rem)] md:min-h-96 md:grid-cols-[220px_1fr] md:overflow-hidden">
      <aside className="space-y-3 md:min-h-0 md:overflow-y-auto md:pr-2">
        <ChipGroup legend="Source" options={facets.source} selected={sources} onToggle={(v) => setSources((s) => toggle(s, v))} />
        <ChipGroup legend="Region" options={facets.region} selected={regions} onToggle={(v) => setRegions((s) => toggle(s, v))} />
        <ChipGroup legend="Remote" options={facets.remote} selected={remotes} onToggle={(v) => setRemotes((s) => toggle(s, v))} />
        <ChipGroup legend="Seniority" options={facets.seniority} selected={seniorities} onToggle={(v) => setSeniorities((s) => toggle(s, v))} />
        <ChipGroup legend="Stack" options={facets.stack} selected={stacks} onToggle={(v) => setStacks((s) => toggle(s, v))} />
        <label className="flex cursor-pointer items-center gap-2 text-sm text-muted">
          <input
            type="checkbox"
            checked={dachOnly}
            onChange={(e) => setDachOnly(e.target.checked)}
            className="size-4 accent-[var(--accent)]"
          />
          DACH-friendly only
        </label>
        <label className="flex cursor-pointer items-center gap-2 text-sm text-muted">
          <input
            type="checkbox"
            checked={salaryOnly}
            onChange={(e) => setSalaryOnly(e.target.checked)}
            className="size-4 accent-[var(--accent)]"
          />
          Salary stated only
        </label>
      </aside>

      <div className="min-w-0 md:flex md:min-h-0 md:flex-col">
        <div className="mb-4 flex flex-wrap items-center gap-3">
          <div className="relative flex-1 min-w-[200px]">
            <label htmlFor="feed-search" className="sr-only">
              Search job titles and companies
            </label>
            <input
              id="feed-search"
              type="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search title or company…"
              className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground placeholder:text-faint focus:border-accent"
            />
          </div>
          <label htmlFor="feed-sort" className="sr-only">
            Sort order
          </label>
          <select
            id="feed-sort"
            value={sort}
            onChange={(e) => setSort(e.target.value as Sort)}
            className="rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-accent"
          >
            <option value="newest">Newest first</option>
            <option value="oldest">Oldest first</option>
          </select>
        </div>

        <div className="mb-3 flex items-center justify-between text-sm">
          <p aria-live="polite" className="text-muted">
            <span className="font-mono text-foreground">{filtered.length}</span>{" "}
            {filtered.length === 1 ? "match" : "matches"}
            {activeCount > 0 && <span className="text-faint"> · {activeCount} filters</span>}
          </p>
          {(activeCount > 0 || search) && (
            <button
              type="button"
              onClick={clearAll}
              className="text-xs text-muted underline decoration-border-strong underline-offset-2 hover:text-foreground"
            >
              Clear all
            </button>
          )}
        </div>

        {filtered.length === 0 ? (
          <div className="rounded-lg border border-dashed border-border-strong bg-surface px-6 py-14 text-center">
            <p className="font-mono text-sm text-accent">// no matches</p>
            <p className="mt-2 text-sm text-muted">
              Nothing fits these filters. Try widening them or clearing the search.
            </p>
          </div>
        ) : (
          <ul className="divide-y divide-border rounded-lg border border-border bg-surface md:min-h-0 md:flex-1 md:overflow-y-auto">
            {filtered.slice(0, RENDER_CAP).map((posting) => (
              <li
                key={posting.id}
                className="group relative flex flex-col gap-1.5 px-4 py-3.5 transition-colors hover:bg-surface-raised"
              >
                <div className="flex items-baseline justify-between gap-3">
                  <Link
                    href={`/job/${posting.id}`}
                    className="font-medium leading-snug transition-colors group-hover:text-accent after:absolute after:inset-0 after:content-['']"
                  >
                    {posting.title}
                  </Link>
                  <time
                    dateTime={posting.first_seen_at}
                    className="shrink-0 font-mono text-xs text-faint"
                    // relative time can tick over between server render and
                    // hydration; the client value is the fresher one anyway
                    suppressHydrationWarning
                  >
                    {relativeTime(posting.first_seen_at)}
                  </time>
                </div>
                <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-muted">
                  <span className="text-foreground/80">{posting.company}</span>
                  {posting.enrichments?.region && posting.enrichments.region !== "Unknown" && (
                    <>
                      <span aria-hidden className="text-faint">·</span>
                      <span>{posting.enrichments.region}</span>
                    </>
                  )}
                  {posting.enrichments?.remote_policy &&
                    posting.enrichments.remote_policy !== "unknown" && (
                      <span className="rounded-sm bg-surface-raised px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-wide text-muted">
                        {posting.enrichments.remote_policy}
                      </span>
                    )}
                  {posting.enrichments?.seniority && (
                    <span className="rounded-sm bg-surface-raised px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-wide text-muted">
                      {posting.enrichments.seniority}
                    </span>
                  )}
                  {formatSalary(
                    posting.enrichments?.salary_min,
                    posting.enrichments?.salary_max,
                    posting.enrichments?.salary_currency,
                  ) && (
                    <span className="rounded-sm border border-accent/40 bg-accent/10 px-1.5 py-0.5 font-mono text-[10px] text-accent">
                      {formatSalary(
                        posting.enrichments?.salary_min,
                        posting.enrichments?.salary_max,
                        posting.enrichments?.salary_currency,
                      )}
                    </span>
                  )}
                  {posting.sources?.name && (
                    <span className="rounded-sm border border-border px-1.5 py-0.5 font-mono text-[10px] text-faint">
                      {posting.sources.name}
                    </span>
                  )}
                  <a
                    href={posting.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="relative z-10 ml-auto text-xs text-faint underline decoration-border-strong underline-offset-2 hover:text-accent"
                    aria-label={`Original posting for ${posting.title} at ${posting.company}`}
                  >
                    original ↗
                  </a>
                </div>
                {posting.enrichments?.summary && (
                  <p className="text-sm leading-snug text-muted">
                    <span
                      className="mr-1.5 rounded-sm border border-accent/40 bg-accent/10 px-1 py-px font-mono text-[9px] uppercase tracking-wider text-accent"
                      title="Summary generated by the LLM enrichment layer"
                    >
                      AI
                    </span>
                    {posting.enrichments.summary}
                  </p>
                )}
                {(posting.enrichments?.stack?.length ?? 0) > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {posting.enrichments!.stack!.slice(0, 8).map((s) => (
                      <span
                        key={s}
                        className="rounded border border-border/60 px-1.5 py-0.5 font-mono text-[10px] text-accent/80"
                      >
                        {s}
                      </span>
                    ))}
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
        {filtered.length > RENDER_CAP && (
          <p className="mt-3 text-center text-xs text-faint">
            Showing first {RENDER_CAP} of {filtered.length}. Narrow the filters to see more.
          </p>
        )}
      </div>
    </div>
  );
}
