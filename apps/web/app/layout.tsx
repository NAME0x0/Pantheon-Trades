import "../styles/globals.css";
import type { Metadata } from "next";
import Link from "next/link";
import { Cinzel, Cormorant_Garamond, JetBrains_Mono } from "next/font/google";
import { Analytics } from "@vercel/analytics/next";

import { ChainTicker } from "@/components/chain-ticker";
import { ThemeToggle, themeInitScript } from "@/components/theme-toggle";
import { ScrollProgress } from "@/components/widgets";
import { BRAND_MARK } from "@/lib/cdn";

const cinzel = Cinzel({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-display",
  display: "swap",
});

const cormorant = Cormorant_Garamond({
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700"],
  style: ["normal", "italic"],
  variable: "--font-serif",
  display: "swap",
});

const mono = JetBrains_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "Pantheon Trades — A council of ten gods debates every trade",
    template: "%s · Pantheon Trades",
  },
  description:
    "A ten-agent AI council debates every Polymarket trade. Every approval — and every restraint — is anchored on Circle's Arc Testnet.",
  metadataBase: new URL("https://pantheon-trades-web.vercel.app"),
  openGraph: {
    title: "Pantheon Trades",
    description:
      "A ten-agent AI council debates every prediction-market trade and anchors every restraint on-chain.",
    type: "website",
    siteName: "Pantheon Trades",
  },
  twitter: {
    card: "summary_large_image",
    title: "Pantheon Trades",
    description:
      "A ten-agent AI council debates every prediction-market trade.",
  },
};

const NAV = [
  { href: "/", label: "Overview" },
  { href: "/demo", label: "Demo" },
  { href: "/dashboard", label: "Dashboard" },
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      className={`${cinzel.variable} ${cormorant.variable} ${mono.variable}`}
      suppressHydrationWarning
    >
      <head>
        {/* No-flash theme init: runs before React hydrates, sets the
            class on <html> from localStorage / system preference. */}
        <script dangerouslySetInnerHTML={{ __html: themeInitScript }} />
      </head>
      <body className="min-h-screen bg-background font-sans text-foreground antialiased">
        <ScrollProgress />
        <ChainTicker />

        <header className="sticky top-0 z-40 border-b border-primary/12 bg-background/70 backdrop-blur-xl">
          <nav className="mx-auto flex max-w-6xl items-center justify-between px-6 py-5">
            <Link
              href="/"
              className="group flex items-center gap-3 transition-opacity hover:opacity-90"
            >
              {/* Iconify CDN — gold-tinted Greek temple line art */}
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={BRAND_MARK}
                alt="Pantheon Trades emblem"
                width={34}
                height={34}
                className="drop-shadow-[0_0_12px_hsl(var(--primary)/0.25)]"
              />
              <div className="flex flex-col leading-none">
                <span className="display text-base font-semibold tracking-[0.32em] text-foreground">
                  PANTHEON
                </span>
                <span className="display mt-1 text-[10px] font-medium tracking-[0.45em] text-primary">
                  TRADES
                </span>
              </div>
            </Link>
            <div className="flex items-center gap-8">
              <ul className="display hidden gap-8 text-[11px] uppercase tracking-[0.3em] md:flex">
                {NAV.map((item) => (
                  <li key={item.href}>
                    <Link
                      href={item.href}
                      className="relative text-muted-foreground transition-colors hover:text-primary"
                    >
                      {item.label}
                      <span className="absolute -bottom-1 left-0 h-px w-0 bg-primary transition-all duration-300 group-hover:w-full" />
                    </Link>
                  </li>
                ))}
              </ul>
              <ThemeToggle />
            </div>
          </nav>
        </header>

        <main className="mx-auto max-w-6xl px-6">{children}</main>

        <footer className="mx-auto mt-24 max-w-6xl px-6 pb-12 pt-16">
          <div className="rule mx-auto mb-10 max-w-xs" />
          <div className="text-center">
            <div className="display mb-6 text-[10px] uppercase tracking-[0.45em] text-primary/80">
              ✦  ΠΑΝΘΕΟΝ  ✦  ΤRADES  ✦
            </div>
            <p className="serif mx-auto max-w-xl text-base italic leading-relaxed text-muted-foreground">
              &ldquo;The council deliberates. Areopagus gates. Parthenon anchors on Arc Testnet.
              Discipline is alpha. Restraint is witnessed.&rdquo;
            </p>
            <div className="mono mt-8 flex flex-wrap items-center justify-center gap-x-5 gap-y-2 text-[10px] uppercase tracking-[0.25em] text-muted-foreground/60">
              <a
                href="https://github.com/NAME0x0/Pantheon-Trades"
                target="_blank"
                rel="noopener noreferrer"
                className="transition-colors hover:text-primary"
              >
                Source
              </a>
              <span>·</span>
              <a
                href="https://testnet.arcscan.app/address/0x4b35CE4Bf71B976205f60Fda1EBAb82eD4D34895"
                target="_blank"
                rel="noopener noreferrer"
                className="transition-colors hover:text-primary"
              >
                On Arc
              </a>
              <span>·</span>
              <Link href="/demo" className="transition-colors hover:text-primary">
                Live demo
              </Link>
              <span>·</span>
              <a
                href="https://polymarket.com"
                target="_blank"
                rel="noopener noreferrer"
                className="transition-colors hover:text-primary"
              >
                Polymarket
              </a>
            </div>
          </div>
        </footer>

        <Analytics />
      </body>
    </html>
  );
}
