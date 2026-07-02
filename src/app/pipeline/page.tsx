import type { Metadata } from "next";
import { getSupabase } from "@/lib/supabase";
import { relativeTime } from "@/lib/format";

export const revalidate = 300;

export const metadata: Metadata = {
  title: "Pipeline",
  description:
    "Live observability for the JobRadar ingestion pipeline: run history, throughput, and per-source health.",
};

type Run = {
  id: number;
  started_at: string;
  finished_at: string | null;
  fetched: number;
  new_postings: number;
  enriched: number;
  failed: number;
  tokens_used: number;
  duration_s: number | null;
  notes: string;
};

type SourceHealth = {
  name: string;
  last_run_at: string | null;
  postings: number;
};

const FRESH_MS = 12 * 60 * 60 * 1000;

async function loadData() {
  const supabase = getSupabase();
  if (!supabase) return null;

  const [runsRes, sourcesRes, postingsRes, enrichedRes] = await Promise.all([
    supabase
      .from("pipeline_runs")
      .select("*")
      .order("started_at", { ascending: false })
      .limit(30),
    supabase.from("sources").select("id, name, last_run_at"),
    supabase.from("postings").select("id", { count: "exact", head: true }),
    supabase.from("enrichments").select("posting_id", { count: "exact", head: true }),
  ]);

  if (runsRes.error || sourcesRes.error) return null;

  const sources: SourceHealth[] = await Promise.all(
    (sourcesRes.data ?? []).map(async (s) => {
      const { count } = await supabase
        .from("postings")
        .select("id", { count: "exact", head: true })
        .eq("source_id", s.id);
      return { name: s.name, last_run_at: s.last_run_at, postings: count ?? 0 };
    }),
  );
  sources.sort((a, b) => b.postings - a.postings);

  return {
    runs: (runsRes.data ?? []) as Run[],
    sources,
    totalPostings: postingsRes.count ?? 0,
    totalEnriched: enrichedRes.count ?? 0,
  };
}

function StatCard({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-lg border border-border bg-surface px-4 py-3">
      <p className="font-mono text-[11px] uppercase tracking-wider text-faint">{label}</p>
      <p className="mt-1 text-xl font-semibold tabular-nums">{value}</p>
      {hint && <p className="mt-0.5 text-xs text-muted">{hint}</p>}
    </div>
  );
}

export default async function PipelinePage() {
  const data = await loadData();

  if (!data) {
    return (
      <main id="main" className="mx-auto max-w-5xl px-4 py-10">
        <h1 className="text-2xl font-semibold tracking-tight">Pipeline</h1>
        <p className="mt-4 text-sm text-muted">Observability data is not available right now.</p>
      </main>
    );
  }

  const { runs, sources, totalPostings, totalEnriched } = data;
  const lastRun = runs[0];
  const coverage = totalPostings > 0 ? Math.round((totalEnriched / totalPostings) * 100) : 0;

  return (
    <main id="main" className="mx-auto max-w-5xl px-4 py-10">
      <div className="mb-8">
        <h1 className="text-2xl font-semibold tracking-tight">Pipeline</h1>
        <p className="mt-1 max-w-2xl text-sm text-muted">
          The machinery, in the open: a Python pipeline on a GitHub Actions cron
          fetches every 6 hours, dedupes across sources, and enriches every posting.
          This page reads the same run metrics the pipeline records about itself.
        </p>
      </div>

      <section aria-labelledby="stats-heading" className="mb-10">
        <h2 id="stats-heading" className="sr-only">
          Key metrics
        </h2>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <StatCard label="Postings tracked" value={totalPostings.toLocaleString("en-US")} />
          <StatCard
            label="Enrichment coverage"
            value={`${coverage}%`}
            hint={`${totalEnriched.toLocaleString("en-US")} enriched`}
          />
          <StatCard label="Runs recorded" value={String(runs.length >= 30 ? "30+" : runs.length)} />
          <StatCard
            label="Last run"
            value={lastRun ? relativeTime(lastRun.started_at) : "never"}
            hint={lastRun ? `${lastRun.new_postings} new postings` : undefined}
          />
        </div>
      </section>

      <section aria-labelledby="sources-heading" className="mb-10">
        <h2 id="sources-heading" className="mb-3 text-lg font-medium">
          Source health
        </h2>
        <ul className="grid gap-3 sm:grid-cols-3">
          {sources.map((s) => {
            const fresh =
              s.last_run_at && Date.now() - Date.parse(s.last_run_at) < FRESH_MS;
            return (
              <li key={s.name} className="rounded-lg border border-border bg-surface px-4 py-3">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-sm">{s.name}</span>
                  <span
                    className={
                      "flex items-center gap-1.5 text-xs " +
                      (fresh ? "text-accent" : "text-warn")
                    }
                  >
                    <span
                      aria-hidden
                      className={
                        "size-1.5 rounded-full " + (fresh ? "bg-accent" : "bg-warn")
                      }
                    />
                    {fresh ? "healthy" : "stale"}
                  </span>
                </div>
                <p className="mt-2 text-sm text-muted">
                  <span className="tabular-nums text-foreground">
                    {s.postings.toLocaleString("en-US")}
                  </span>{" "}
                  postings
                </p>
                <p className="text-xs text-faint">
                  last fetched {s.last_run_at ? relativeTime(s.last_run_at) : "never"}
                </p>
              </li>
            );
          })}
        </ul>
      </section>

      <section aria-labelledby="runs-heading">
        <h2 id="runs-heading" className="mb-3 text-lg font-medium">
          Run history
        </h2>
        {runs.length === 0 ? (
          <p className="text-sm text-muted">No runs recorded yet.</p>
        ) : (
          <div className="overflow-x-auto rounded-lg border border-border bg-surface">
            <table className="w-full min-w-[640px] text-sm">
              <thead>
                <tr className="border-b border-border text-left font-mono text-[11px] uppercase tracking-wider text-faint">
                  <th scope="col" className="px-4 py-2.5 font-medium">Started</th>
                  <th scope="col" className="px-4 py-2.5 text-right font-medium">Fetched</th>
                  <th scope="col" className="px-4 py-2.5 text-right font-medium">New</th>
                  <th scope="col" className="px-4 py-2.5 text-right font-medium">Enriched</th>
                  <th scope="col" className="px-4 py-2.5 text-right font-medium">Tokens</th>
                  <th scope="col" className="px-4 py-2.5 text-right font-medium">Duration</th>
                  <th scope="col" className="px-4 py-2.5 font-medium">Notes</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {runs.map((run) => (
                  <tr key={run.id} className="text-muted">
                    <td className="px-4 py-2.5 whitespace-nowrap">
                      <time dateTime={run.started_at} title={run.started_at}>
                        {relativeTime(run.started_at)}
                      </time>
                    </td>
                    <td className="px-4 py-2.5 text-right tabular-nums">{run.fetched}</td>
                    <td className="px-4 py-2.5 text-right tabular-nums text-foreground">
                      {run.new_postings}
                    </td>
                    <td className="px-4 py-2.5 text-right tabular-nums">{run.enriched}</td>
                    <td className="px-4 py-2.5 text-right tabular-nums">
                      {run.tokens_used || "–"}
                    </td>
                    <td className="px-4 py-2.5 text-right tabular-nums">
                      {run.duration_s != null ? `${Number(run.duration_s).toFixed(1)}s` : "–"}
                    </td>
                    <td className="max-w-[220px] truncate px-4 py-2.5 text-xs" title={run.notes}>
                      {run.notes || ""}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <p className="mt-3 text-xs text-faint">
          A run that enriches only part of the backlog is a normal, visible state,
          not a bug: free LLM quotas are bounded, so enrichment is designed to be
          resumable across runs.
        </p>
      </section>
    </main>
  );
}
