import "../styles/globals.css";
import type { Metadata } from "next";
import Link from "next/link";
import Image from "next/image";
import { Cinzel, Cormorant_Garamond, JetBrains_Mono } from "next/font/google";
import { Analytics } from "@vercel/analytics/next";

const cinzel = Cinzel({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-display",
  display: "swap",
});

const cormorant = Cormorant_Garamond({
  subsets: ["latin"],
  weight: ["300", "400", "500", "600"],
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
    default: "Pantheon Trades — AI council deliberation for prediction markets",
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
      className={`dark ${cinzel.variable} ${cormorant.variable} ${mono.variable}`}
    >
      <body className="min-h-screen bg-background font-sans text-foreground antialiased">
        {/* Subtle parchment / marble veining behind everything */}
        <div
          aria-hidden
          className="pointer-events-none fixed inset-0 -z-10 opacity-[0.04]"
          style={{
            backgroundImage:
              "radial-gradient(circle at 20% 10%, rgba(200,168,90,0.6), transparent 45%), radial-gradient(circle at 80% 70%, rgba(247,243,233,0.4), transparent 50%)",
          }}
        />
        <header className="border-b border-primary/25 bg-background/85 backdrop-blur-md">
          <nav className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
            <Link
              href="/"
              className="group flex items-center gap-3 text-primary transition-opacity hover:opacity-90"
            >
              <Image
                src="/mark.svg"
                alt=""
                width={36}
                height={36}
                priority
                className="drop-shadow-[0_0_8px_rgba(200,168,90,0.25)]"
              />
              <span className="font-display text-lg font-semibold tracking-[0.32em]">
                PANTHEON&nbsp;TRADES
              </span>
            </Link>
            <ul className="flex gap-7 font-display text-xs uppercase tracking-[0.22em]">
              {NAV.map((item) => (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    className="text-muted-foreground transition-colors hover:text-primary"
                  >
                    {item.label}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>
        </header>
        <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>
        <footer className="mx-auto mt-16 max-w-6xl border-t border-primary/20 px-6 py-8 text-center">
          <Image
            src="/meander.svg"
            alt=""
            width={240}
            height={16}
            className="mx-auto mb-4 opacity-70"
          />
          <p className="font-serif text-sm italic text-muted-foreground">
            The council deliberates. Areopagus gates. Parthenon anchors on Arc Testnet.
          </p>
        </footer>
        <Analytics />
      </body>
    </html>
  );
}
