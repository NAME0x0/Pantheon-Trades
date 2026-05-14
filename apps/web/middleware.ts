import { NextRequest, NextResponse } from "next/server";

// Pages that require a session cookie. Everything else (signin, public
// overview, traces) renders without auth.
const PROTECTED_PREFIXES = ["/trades", "/passports", "/olympus"];

export function middleware(req: NextRequest): NextResponse {
  const { pathname } = req.nextUrl;
  const needsAuth = PROTECTED_PREFIXES.some((p) => pathname.startsWith(p));
  if (!needsAuth) {
    return NextResponse.next();
  }
  const token = req.cookies.get("pantheon_token")?.value;
  if (!token) {
    const url = req.nextUrl.clone();
    url.pathname = "/signin";
    url.searchParams.set("next", pathname);
    return NextResponse.redirect(url);
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next|favicon.ico|public).*)"],
};
