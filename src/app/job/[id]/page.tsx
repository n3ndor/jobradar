import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getSupabase } from "@/lib/supabase";
import { relativeTime } from "@/lib/format";
import { BackToFeed } from "@/components/BackToFeed";

export const revalidate = 300;

type Props = { params: Promise<{ id: string }> };

type DetailRow = {
  id: number;
  company: string;
  title: string;
  url: string;
  location_raw: string;
  posted_at: string | null;
  first_seen_at: string;
  raw: Record<string, unknown>;
  sources: { name: string } | null;
  enrichments: {
    seniority: string | null;
    stack: string[] | null;
    region: string | null;
    remote_policy: string | null;
    dach_friendly: boolean | null;
    summary: string | null;
    salary_min: number | null;
    salary_max: number | null;
    salary_currency: string | null;
    model: string | null;
    status: string | null;
  } | null;
};

async function loadJob(id: string): Promise<DetailRow | null> {
  if (!/^\d+$/.test(id)) return null;
  const supabase = getSupabase();
  if (!supabase) return null;
  const { data, error } = await supabase
    .from("postings")
    .select(
      "id, company, title, url, location_raw, posted_at, first_seen_at, raw, sources(name), enrichments(*)",
    )
    .eq("id", Number(id))
    .maybeSingle();
  if (error || !data) return null;
  const row = data as unknown as Record<string, unknown>;
  return {
    ...row,
    enrichments: Array.isArray(row.enrichments)
      ? (row.enrichments[0] ?? null)
      : (row.enrichments ?? null),
  } as DetailRow;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { id } = await params;
  const job = await loadJob(id);
  return {
    title: job ? `${job.title} at ${job.company}` : "Job not found",
  };
}

function stripHtml(html: string): string {
  return html
    .replace(/<\/(p|div|li|ul|ol|h[1-6]|br)>/gi, "\n")
    .replace(/<br\s*\/?>/gi, "\n")
    .replace(/<[^>]+>/g, " ")
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&#39;/g, "'")
    .replace(/&quot;/g, '"')
    .replace(/&nbsp;/g, " ")
    .replace(/[ \t]+/g, " ")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-4 py-2">
      <dt className="font-mono text-[11px] uppercase tracking-wider text-faint">{label}</dt>
      <dd className="text-right text-sm">{children}</dd>
    </div>
  );
}

function formatSalary(e: NonNullable<DetailRow["enrichments"]>): string | null {
  if (e.salary_min == null && e.salary_max == null) return null;
  const fmt = (n: number) => n.toLocaleString("en-US");
  const cur = e.salary_currency ?? "";
  if (e.salary_min != null && e.salary_max != null)
    return `${fmt(e.salary_min)}–${fmt(e.salary_max)} ${cur}`.trim();
  return `${fmt((e.salary_min ?? e.salary_max)!)} ${cur}`.trim();
}

export default async function JobDetailPage({ params }: Props) {
  const { id } = await params;
  const job = await loadJob(id);
  if (!job) notFound();

  const e = job.enrichments;
  const description =
    typeof job.raw?.description === "string" ? stripHtml(job.raw.description) : "";
  const rawWithoutDescription = { ...job.raw };
  delete rawWithoutDescription.description;
  const salary = e ? formatSalary(e) : null;

  return (
    <main id="main" className="mx-auto max-w-5xl px-4 py-10">
      <nav aria-label="Breadcrumb" className="mb-6 text-sm">
        <BackToFeed />
      </nav>

      <header className="mb-8">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">{job.title}</h1>
            <p className="mt-1 text-sm text-muted">
              {job.company}
              {job.location_raw && <> · {job.location_raw}</>}
              {job.sources?.name && (
                <span className="ml-2 rounded-sm border border-border px-1.5 py-0.5 font-mono text-[10px] text-faint">
                  {job.sources.name}
                </span>
              )}
            </p>
            <p className="mt-1 font-mono text-xs text-faint">
              first seen {relativeTime(job.first_seen_at)}
              {job.posted_at && <> · posted {relativeTime(job.posted_at)}</>}
            </p>
          </div>
          <a
            href={job.url}
            target="_blank"
            rel="noopener noreferrer"
            className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-background transition-opacity hover:opacity-90"
          >
            View original posting ↗
          </a>
        </div>
      </header>

      <div className="grid gap-4 md:grid-cols-2">
        <section
          aria-labelledby="extracted-heading"
          className="rounded-lg border border-border bg-surface p-5"
        >
          <h2 id="extracted-heading" className="mb-1 text-base font-medium">
            Extracted fields
          </h2>
          <p className="mb-3 text-xs text-faint">
            {e?.status === "ok"
              ? `Rules + ${e.model ?? "LLM"} extraction.`
              : "Deterministic rules extraction; LLM summary pending."}
          </p>
          {e ? (
            <dl className="divide-y divide-border">
              <Field label="Region">{e.region ?? "–"}</Field>
              <Field label="Remote policy">{e.remote_policy ?? "–"}</Field>
              <Field label="Seniority">{e.seniority ?? "–"}</Field>
              <Field label="DACH-friendly">{e.dach_friendly ? "yes" : "no"}</Field>
              {salary && <Field label="Salary (parsed)">{salary}</Field>}
              <Field label="Stack">
                {(e.stack?.length ?? 0) > 0 ? (
                  <span className="flex flex-wrap justify-end gap-1">
                    {e.stack!.map((s) => (
                      <span
                        key={s}
                        className="rounded border border-border/60 px-1.5 py-0.5 font-mono text-[10px] text-accent/80"
                      >
                        {s}
                      </span>
                    ))}
                  </span>
                ) : (
                  "–"
                )}
              </Field>
              {e.summary && (
                <div className="py-2">
                  <dt className="mb-1 font-mono text-[11px] uppercase tracking-wider text-faint">
                    AI summary
                  </dt>
                  <dd className="text-sm text-muted">{e.summary}</dd>
                </div>
              )}
            </dl>
          ) : (
            <p className="text-sm text-muted">Not enriched yet.</p>
          )}
        </section>

        <section
          aria-labelledby="raw-heading"
          className="rounded-lg border border-border bg-surface p-5"
        >
          <h2 id="raw-heading" className="mb-1 text-base font-medium">
            Raw source data
          </h2>
          <p className="mb-3 text-xs text-faint">
            Exactly what the source API returned, so extraction quality is checkable.
          </p>
          <pre className="max-h-80 overflow-auto rounded-md bg-background p-3 font-mono text-xs leading-relaxed text-muted">
            {JSON.stringify(rawWithoutDescription, null, 2)}
          </pre>
        </section>
      </div>

      {description && (
        <section
          aria-labelledby="description-heading"
          className="mt-4 rounded-lg border border-border bg-surface p-5"
        >
          <h2 id="description-heading" className="mb-3 text-base font-medium">
            Description
            <span className="ml-2 font-mono text-[10px] uppercase tracking-wider text-faint">
              as provided by source, may be truncated
            </span>
          </h2>
          <p className="max-h-96 overflow-y-auto whitespace-pre-wrap text-sm leading-relaxed text-muted">
            {description}
          </p>
        </section>
      )}
    </main>
  );
}
