/**
 * Polymarket proxy — Vercel Edge runtime.
 *
 * Why this exists: Polymarket geo-blocks several jurisdictions at the
 * HTTP layer. DNS resolves, the TCP handshake gets refused. From the
 * operator's network we can't reach https://gamma-api.polymarket.com
 * or https://clob.polymarket.com at all.
 *
 * Vercel's edge network runs in permitted regions by default, so a
 * thin pass-through proxy hosted on Vercel Edge gets us full read +
 * write access to Polymarket without any other infra change.
 *
 * Routes:
 *   /api/polymarket-proxy/gamma/...    -> https://gamma-api.polymarket.com/...
 *   /api/polymarket-proxy/clob/...     -> https://clob.polymarket.com/...
 *   /api/polymarket-proxy/data/...     -> https://data-api.polymarket.com/...
 *
 * Configuration on the Pantheon side:
 *   POLYMARKET_HOST=https://pantheon-trades-web.vercel.app/api/polymarket-proxy/clob
 *   POLYMARKET_GAMMA=https://pantheon-trades-web.vercel.app/api/polymarket-proxy/gamma
 *
 * Headers:
 *   - Forwards Authorization, POLY-API-KEY, POLY-PASSPHRASE,
 *     POLY-SIGNATURE, POLY-TIMESTAMP, Content-Type (every header
 *     Polymarket's L2 auth needs).
 *   - Strips inbound cookies + Host header so the upstream sees a
 *     clean request.
 *
 * Optional shared-secret guard:
 *   - Set POLYMARKET_PROXY_TOKEN in Vercel env. Clients must include
 *     `x-pantheon-proxy: <token>` header. Without the token, the
 *     proxy is open to the world (fine for read-only; reckless if
 *     you're routing signed orders through it).
 *
 * What this does NOT do:
 *   - Cache anything. Read responses go straight through.
 *   - Modify request bodies. Signed orders are byte-stable end-to-end.
 *   - Rate-limit. Add slowapi-on-edge or Vercel rate-limit hooks
 *     if you start seeing abuse.
 */

import { NextRequest, NextResponse } from "next/server";

export const runtime = "edge";

const UPSTREAM_MAP: Record<string, string> = {
  gamma: "https://gamma-api.polymarket.com",
  clob: "https://clob.polymarket.com",
  data: "https://data-api.polymarket.com",
};

// Headers we forward verbatim. Everything else gets dropped.
const FORWARD_REQUEST_HEADERS = new Set([
  "authorization",
  "content-type",
  "accept",
  "accept-encoding",
  "user-agent",
  "poly-api-key",
  "poly-passphrase",
  "poly-signature",
  "poly-timestamp",
  "poly-address",
]);

// Headers we drop from the upstream response — Vercel adds its own.
const STRIP_RESPONSE_HEADERS = new Set([
  "content-encoding",
  "content-length",
  "transfer-encoding",
  "connection",
]);

async function proxy(req: NextRequest, params: { path?: string[] }) {
  const pathSegments = params.path ?? [];
  if (pathSegments.length === 0) {
    return new NextResponse(
      JSON.stringify({ error: "missing route segment" }),
      { status: 400, headers: { "content-type": "application/json" } },
    );
  }
  const venue = pathSegments[0];
  const upstreamBase = UPSTREAM_MAP[venue];
  if (!upstreamBase) {
    return new NextResponse(
      JSON.stringify({ error: `unknown venue: ${venue}`, allowed: Object.keys(UPSTREAM_MAP) }),
      { status: 404, headers: { "content-type": "application/json" } },
    );
  }

  // Optional shared-secret guard.
  const expectedToken = process.env.POLYMARKET_PROXY_TOKEN;
  if (expectedToken) {
    const presented = req.headers.get("x-pantheon-proxy");
    if (presented !== expectedToken) {
      return new NextResponse(
        JSON.stringify({ error: "missing or invalid x-pantheon-proxy header" }),
        { status: 401, headers: { "content-type": "application/json" } },
      );
    }
  }

  const upstreamPath = pathSegments.slice(1).join("/");
  const url = new URL(req.url);
  const upstreamUrl = `${upstreamBase}/${upstreamPath}${url.search}`;

  // Build forwarded headers.
  const upstreamHeaders = new Headers();
  for (const [key, value] of req.headers.entries()) {
    if (FORWARD_REQUEST_HEADERS.has(key.toLowerCase())) {
      upstreamHeaders.set(key, value);
    }
  }
  // Always identify ourselves clearly for the upstream's logs.
  if (!upstreamHeaders.has("user-agent")) {
    upstreamHeaders.set("user-agent", "Pantheon-Trades/1.0 (+vercel-edge-proxy)");
  }

  // Body pass-through for non-GET methods. Edge runtime gives us
  // a ReadableStream we can re-emit.
  const init: RequestInit = {
    method: req.method,
    headers: upstreamHeaders,
    redirect: "follow",
  };
  if (req.method !== "GET" && req.method !== "HEAD") {
    init.body = await req.arrayBuffer();
  }

  let upstream: Response;
  try {
    upstream = await fetch(upstreamUrl, init);
  } catch (err) {
    return new NextResponse(
      JSON.stringify({
        error: "upstream fetch failed",
        upstream: upstreamUrl,
        detail: err instanceof Error ? err.message : String(err),
      }),
      { status: 502, headers: { "content-type": "application/json" } },
    );
  }

  // Build the downstream response from the upstream body + headers.
  const respHeaders = new Headers();
  upstream.headers.forEach((v, k) => {
    if (!STRIP_RESPONSE_HEADERS.has(k.toLowerCase())) {
      respHeaders.set(k, v);
    }
  });
  // CORS for browser-side callers (the /demo page on the same origin
  // doesn't need this; external dev callers might).
  respHeaders.set("access-control-allow-origin", "*");
  respHeaders.set("access-control-allow-headers", "content-type, authorization, x-pantheon-proxy, poly-api-key, poly-passphrase, poly-signature, poly-timestamp, poly-address");
  respHeaders.set("access-control-allow-methods", "GET, POST, PUT, DELETE, OPTIONS");

  return new NextResponse(upstream.body, {
    status: upstream.status,
    headers: respHeaders,
  });
}

export async function GET(req: NextRequest, ctx: { params: { path?: string[] } }) {
  return proxy(req, ctx.params);
}

export async function POST(req: NextRequest, ctx: { params: { path?: string[] } }) {
  return proxy(req, ctx.params);
}

export async function PUT(req: NextRequest, ctx: { params: { path?: string[] } }) {
  return proxy(req, ctx.params);
}

export async function DELETE(req: NextRequest, ctx: { params: { path?: string[] } }) {
  return proxy(req, ctx.params);
}

export async function OPTIONS() {
  return new NextResponse(null, {
    status: 204,
    headers: {
      "access-control-allow-origin": "*",
      "access-control-allow-headers": "content-type, authorization, x-pantheon-proxy, poly-api-key, poly-passphrase, poly-signature, poly-timestamp, poly-address",
      "access-control-allow-methods": "GET, POST, PUT, DELETE, OPTIONS",
      "access-control-max-age": "86400",
    },
  });
}
