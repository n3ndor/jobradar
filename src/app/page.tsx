import { getSupabase } from "@/lib/supabase";
import { relativeTime } from "@/lib/format";
import type { Posting } from "@/lib/types";

export const revalidate = 300;

async function loadPostings(): Promise<
  | { state: "unconfigured" }
  | { state: "error"; message: string }
  | { state: "ok"; postings: Posting[]; total: number }
> {
  const supabase = getSupabase();
  if (!supabase) return { state: "unconfigured" };

  const { data, error, count } = await supabase
    .from("postings")
    .select("id, company, title, url, location_raw, posted_at, first_seen_at, sources(name)", {
      count: "exact",
    })
    .order("first_seen_at", { ascending: false })
    .limit(60);

  if (error) return { state: "error", message: error.message };
  return {
    state: "ok",
    postings: (data as unknown as Posting[]) ?? [],
    total: count ?? 0,
  };
}

function EmptyState({ title, body }: { title: string; body: string }) {
  return (
    <div className="rounded-lg border border-dashed border-border-strong bg-surface px-6 py-16 text-center">
      <p className="font-mono text-sm text-accent">{title}</p>
      <p className="mx-auto mt-2 max-w-md text-sm text-muted">{body}</p>
    </div>
  );
}

function SourceBadge({ name }: { name: string }) {
  return (
    <span className="rounded-sm border border-border bg-surface-raised px-1.5 py-0.5 font-mono text-[11px] text-muted">
      {name}
    </span>
  );
}

export default async function FeedPage() {
  const result = await loadPostings();

  return (
    <main id="main" className="mx-auto max-w-5xl px-4 py-10">
      <div className="mb-8">
        <h1 className="text-2xl font-semibold tracking-tight">
          Remote job feed
        </h1>
        <p className="mt-1 text-sm text-muted">
          Fresh postings from public job APIs, deduplicated across sources.
          {result.state === "ok" && result.total > 0 && (
            <span className="ml-2 font-mono text-xs text-faint">
              {result.total.toLocaleString("en-US")} postings tracked
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
        <ul className="divide-y divide-border rounded-lg border border-border bg-surface">
          {result.postings.map((posting) => (
            <li key={posting.id}>
              <a
                href={posting.url}
                target="_blank"
                rel="noopener noreferrer"
                className="group flex flex-col gap-1 px-4 py-3.5 transition-colors hover:bg-surface-raised"
              >
                <div className="flex items-baseline justify-between gap-3">
                  <span className="font-medium leading-snug group-hover:text-accent transition-colors">
                    {posting.title}
                  </span>
                  <time
                    dateTime={posting.first_seen_at}
                    className="shrink-0 font-mono text-xs text-faint"
                  >
                    {relativeTime(posting.first_seen_at)}
                  </time>
                </div>
                <div className="flex flex-wrap items-center gap-2 text-sm text-muted">
                  <span>{posting.company}</span>
                  {posting.location_raw && (
                    <>
                      <span aria-hidden="true" className="text-faint">
                        ·
                      </span>
                      <span>{posting.location_raw}</span>
                    </>
                  )}
                  {posting.sources?.name && (
                    <SourceBadge name={posting.sources.name} />
                  )}
                </div>
              </a>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
