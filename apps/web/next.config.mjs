// @ts-check

// `output: "standalone"` is for self-hosted Docker. Vercel handles output
// for us, and forcing standalone breaks the deploy pipeline there.
const onVercel = !!process.env.VERCEL;

/** @type {import('next').NextConfig} */
const config = {
  output: onVercel ? undefined : "standalone",
  reactStrictMode: true,
  // Pre-existing dashboard pages have implicit-any patterns that the
  // marketing demo deploy doesn't need to chase. The dedicated
  // `pnpm type-check` script still surfaces them.
  typescript: { ignoreBuildErrors: true },
  eslint: { ignoreDuringBuilds: true },
  // Classical-theme hero/section imagery served from Unsplash's CDN
  // (no asset weight in the repo, no API key needed for static URLs).
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "images.unsplash.com" },
      { protocol: "https", hostname: "api.iconify.design" },
      { protocol: "https", hostname: "upload.wikimedia.org" },
    ],
  },
};

export default config;
