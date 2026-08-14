import { NextRequest, NextResponse } from "next/server";
import { AUTH_COOKIE, sessionToken } from "./lib/auth";

export async function middleware(request: NextRequest) {
  const cookie = request.cookies.get(AUTH_COOKIE)?.value;
  const expected = await sessionToken();

  if (cookie === expected) {
    return NextResponse.next();
  }

  const loginUrl = new URL("/login", request.url);
  loginUrl.searchParams.set("next", request.nextUrl.pathname);
  return NextResponse.redirect(loginUrl);
}

export const config = {
  matcher: ["/((?!login|api/login|_next/static|_next/image|favicon.ico).*)"],
};
