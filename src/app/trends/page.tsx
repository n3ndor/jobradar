import type { Metadata } from "next";
import { getSupabase } from "@/lib/supabase";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Trends",
  description:
    "Tech job market trends from enriched posting data: top stacks, regions, seniority, and remote-work split.",
};

type EnrichmentRow = {
  stack: string[] | null;
  seniority: string | null;
  region: string | null;
  remote_policy: string | null;
  dach_friendly: boolean | null;
};

async function loadRows(): Promise<EnrichmentRow[] | null> {
  const supabase = getSupabase();
  if (!supabase) return null;
  const { data, error } = await supabase
    .from("enrichments")
    .select("stack, seniority, region, remote_policy, dach_friendly")
    .limit(1000);
  if (error) return null;
  return data as EnrichmentRow[];
}

function tally(values: (string | null | undefined)[]): [string, number][] {
  const m = new Map<string, number>();
  for (const v of values) {
    if (v) m.set(v, (m.get(v) ?? 0) + 1);
  }
  return [...m.entries()].sort((a, b) => b[1] - a[1]);
}

function BarChart({
  title,
  entries,
  total,
  limit,
}: {
  title: string;
  entries: [string, number][];
  total: number;
  limit?: number;
}) {
  const shown = limit ? entries.slice(0, limit) : entries;
  const max = shown[0]?.[1] ?? 1;
  return (
    <section
      aria-label={title}
      className="rounded-lg border border-border bg-surface p-5"
    >
      <h2 className="mb-4 text-base font-medium">{title}</h2>
      <ul className="space-y-2.5">
        {shown.map(([label, count]) => {
          const pct = Math.round((count / total) * 100);
          return (
            <li key={label} className="grid grid-cols-[110px_1fr_auto] items-center gap-3 text-sm">
              <span className="truncate text-muted" title={label}>
                {label}
              </span>
              <div className="h-2 rounded-full bg-surface-raised" aria-hidden>
                <div
                  className="h-2 rounded-full bg-accent/70"
                  style={{ width: `${Math.max((count / max) * 100, 2)}%` }}
                />
              </div>
              <span className="font-mono text-xs tabular-nums text-faint">
                {count} <span className="text-faint/70">({pct}%)</span>
              </span>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

export default async function TrendsPage() {
  const rows = await loadRows();

  if (!rows || rows.length === 0) {
    return (
      <main id="main" className="mx-auto max-w-5xl px-4 py-10">
        <h1 className="text-2xl font-semibold tracking-tight">Trends</h1>
        <p className="mt-4 text-sm text-muted">
          Not enough enriched data yet. Check back after the next pipeline run.
        </p>
      </main>
    );
  }

  const total = rows.length;
  const stacks = tally(rows.flatMap((r) => r.stack ?? []));
  const regions = tally(rows.map((r) => r.region));
  const seniority = tally(rows.map((r) => r.seniority));
  const remote = tally(rows.map((r) => r.remote_policy));

  const remoteCount = rows.filter((r) => r.remote_policy === "remote").length;
  const dachCount = rows.filter((r) => r.dach_friendly).length;
  const remotePct = Math.round((remoteCount / total) * 100);
  const dachPct = Math.round((dachCount / total) * 100);

  return (
    <main id="main" className="mx-auto max-w-5xl px-4 py-10">
      <div className="mb-8">
        <h1 className="text-2xl font-semibold tracking-tight">Trends</h1>
        <p className="mt-1 max-w-2xl text-sm text-muted">
          What the tech job market looks like across{" "}
          <span className="font-mono text-foreground">{total.toLocaleString("en-US")}</span>{" "}
          currently tracked postings — the aggregate view you cannot get by
          scrolling job boards.
        </p>
      </div>

      <div className="mb-6 grid grid-cols-2 gap-3 sm:max-w-md">
        <div className="rounded-lg border border-border bg-surface px-4 py-3">
          <p className="font-mono text-[11px] uppercase tracking-wider text-faint">
            Fully remote
          </p>
          <p className="mt-1 text-xl font-semibold tabular-nums">{remotePct}%</p>
        </div>
        <div className="rounded-lg border border-border bg-surface px-4 py-3">
          <p className="font-mono text-[11px] uppercase tracking-wider text-faint">
            DACH-friendly
          </p>
          <p className="mt-1 text-xl font-semibold tabular-nums">{dachPct}%</p>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <BarChart title="Top technologies" entries={stacks} total={total} limit={14} />
        <div className="space-y-4">
          <BarChart title="Regions" entries={regions} total={total} limit={9} />
          <BarChart title="Seniority" entries={seniority} total={total} />
          <BarChart title="Remote policy" entries={remote} total={total} />
        </div>
      </div>

      <p className="mt-6 text-xs text-faint">
        Percentages are shares of all tracked postings; a posting can mention
        several technologies. Tags are extracted deterministically from titles
        and descriptions, so they undercount technologies that postings do not
        name explicitly.
      </p>
    </main>
  );
}
