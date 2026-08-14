import "server-only";

export const AUTH_COOKIE = "mt_session";

// Web Crypto (globalThis.crypto.subtle) works in both the Edge middleware
// runtime and the Node.js runtime Vercel uses for server actions/routes,
// so we use it instead of node:crypto to avoid a runtime-specific import.
async function sha256(input: string): Promise<string> {
  const data = new TextEncoder().encode(input);
  const hashBuffer = await crypto.subtle.digest("SHA-256", data);
  return Array.from(new Uint8Array(hashBuffer))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

// Deterministic, non-reversible token derived from the shared dashboard
// password. Avoids storing the raw password in a cookie while still
// letting middleware check it without a database round trip.
export async function sessionToken(): Promise<string> {
  const password = process.env.DASHBOARD_PASSWORD;
  if (!password) {
    throw new Error("Missing DASHBOARD_PASSWORD environment variable.");
  }
  return sha256(`market-trends:${password}`);
}

export function checkPassword(candidate: string): boolean {
  const password = process.env.DASHBOARD_PASSWORD;
  if (!password) return false;
  return candidate === password;
}
