export type Posting = {
  id: number;
  company: string;
  title: string;
  url: string;
  location_raw: string;
  posted_at: string | null;
  first_seen_at: string;
  sources: { name: string } | null;
};
