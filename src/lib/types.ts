export type Enrichment = {
  seniority: string | null;
  stack: string[] | null;
  region: string | null;
  remote_policy: string | null;
  dach_friendly: boolean | null;
  // Populated by the LLM enrichment layer; absent from the feed query.
  summary?: string | null;
  salary_min?: number | null;
  salary_max?: number | null;
  salary_currency?: string | null;
};

export type Posting = {
  id: number;
  company: string;
  title: string;
  url: string;
  location_raw: string;
  posted_at: string | null;
  first_seen_at: string;
  sources: { name: string } | null;
  enrichments: Enrichment | null;
};
