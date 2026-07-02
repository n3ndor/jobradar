import { createClient, type SupabaseClient } from "@supabase/supabase-js";

/**
 * Read-only client for the public dashboard. Returns null when the project
 * is not configured yet so pages can render an honest setup state instead
 * of crashing the build.
 */
export function getSupabase(): SupabaseClient | null {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;
  if (!url || !key) return null;
  return createClient(url, key, { auth: { persistSession: false } });
}
