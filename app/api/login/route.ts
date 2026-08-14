import { NextRequest, NextResponse } from "next/server";
import { AUTH_COOKIE, checkPassword, sessionToken } from "@/lib/auth";

export async function POST(request: NextRequest) {
  const formData = await request.formData();
  const password = String(formData.get("password") ?? "");
  const next = String(formData.get("next") ?? "/");
  const safeNext = next.startsWith("/") ? next : "/";

  if (!checkPassword(password)) {
    const url = new URL("/login", request.url);
    url.searchParams.set("error", "1");
    url.searchParams.set("next", safeNext);
    return NextResponse.redirect(url, { status: 303 });
  }

  const response = NextResponse.redirect(new URL(safeNext, request.url), { status: 303 });
  response.cookies.set(AUTH_COOKIE, await sessionToken(), {
    httpOnly: true,
    secure: true,
    sameSite: "lax",
    path: "/",
    maxAge: 60 * 60 * 24 * 30,
  });
  return response;
}
