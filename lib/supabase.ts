import "server-only";
import { createClient } from "@supabase/supabase-js";

// Server-only client. Uses the service role key, so this must never be
// imported from a client component or exposed to the browser.
export function getServiceClient() {
  const url = process.env.SUPABASE_URL;
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY;

  if (!url || !key) {
    throw new Error(
      "Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY environment variables."
    );
  }

  return createClient(url, key, {
    db: { schema: "market_trends" },
    auth: { persistSession: false },
    // supabase-js issues its queries through fetch, which Next.js caches by
    // default. The pages are already force-dynamic, but pinning no-store
    // here removes any chance of the dashboard serving a stale snapshot of
    // the data after a scrape run has updated it.
    global: {
      fetch: (input, init) => fetch(input, { ...init, cache: "no-store" }),
    },
  });
}
