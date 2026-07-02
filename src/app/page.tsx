import { getSupabase } from "@/lib/supabase";
import type { Posting } from "@/lib/types";
import { FeedExplorer } from "@/components/FeedExplorer";

export const revalidate = 300;

// Client-side filtering runs over the newest postings. PostgREST caps a single
// response at 1000 rows; when the dataset consistently exceeds that, move
// filtering server-side (or paginate).
const FEED_LIMIT = 1000;

async function loadPostings(): Promise<
  | { state: "unconfigured" }
  | { state: "error"; message: string }
  | { state: "ok"; postings: Posting[]; total: number }
> {
  const supabase = getSupabase();
  if (!supabase) return { state: "unconfigured" };

  const { data, error, count } = await supabase
    .from("postings")
    .select(
      "id, company, title, url, location_raw, posted_at, first_seen_at, sources(name), enrichments(seniority, stack, region, remote_policy, dach_friendly, summary, salary_min, salary_max, salary_currency)",
      { count: "exact" },
    )
    .order("first_seen_at", { ascending: false })
    .limit(FEED_LIMIT);

  if (error) return { state: "error", message: error.message };

  // enrichments comes back as an array (or object) depending on relationship detection; normalize.
  const postings = ((data as unknown as Record<string, unknown>[]) ?? []).map((row) => ({
    ...row,
    enrichments: Array.isArray(row.enrichments)
      ? (row.enrichments[0] ?? null)
      : (row.enrichments ?? null),
  })) as Posting[];

  return { state: "ok", postings, total: count ?? 0 };
}

function EmptyState({ title, body }: { title: string; body: string }) {
  return (
    <div className="rounded-lg border border-dashed border-border-strong bg-surface px-6 py-16 text-center">
      <p className="font-mono text-sm text-accent">{title}</p>
      <p className="mx-auto mt-2 max-w-md text-sm text-muted">{body}</p>
    </div>
  );
}

export default async function FeedPage() {
  const result = await loadPostings();

  return (
    <main id="main" className="mx-auto max-w-5xl px-4 py-10">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight">Tech job feed</h1>
        <p className="mt-1 text-sm text-muted">
          Engineering, data, design, and product roles from public job APIs —
          deduplicated, tagged by region, remote policy, seniority, and stack,
          then AI-summarized with salaries parsed straight out of the posting
          text. Tech only, no other industries.
          {result.state === "ok" && result.total > 0 && (
            <span className="ml-1 font-mono text-xs text-faint">
              {result.total.toLocaleString("en-US")} tracked
              {result.total > result.postings.length &&
                `, newest ${result.postings.length.toLocaleString("en-US")} shown`}
              .
            </span>
          )}
        </p>
      </div>

      {result.state === "unconfigured" && (
        <EmptyState
          title="// awaiting configuration"
          body="The dashboard is not connected to the database yet. Set NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY."
        />
      )}

      {result.state === "error" && (
        <EmptyState
          title="// query failed"
          body={`The database rejected the read: ${result.message}`}
        />
      )}

      {result.state === "ok" && result.postings.length === 0 && (
        <EmptyState
          title="// radar warming up"
          body="Schema is live but no postings yet. The next scheduled pipeline run will populate this feed."
        />
      )}

      {result.state === "ok" && result.postings.length > 0 && (
        <FeedExplorer postings={result.postings} />
      )}
    </main>
  );
}
