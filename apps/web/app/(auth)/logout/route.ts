import { NextResponse } from "next/server";

export async function POST(): Promise<NextResponse> {
  const res = NextResponse.json({ ok: true });
  res.cookies.set("pantheon_token", "", { path: "/", maxAge: 0 });
  return res;
}

export async function GET(): Promise<NextResponse> {
  return POST();
}
