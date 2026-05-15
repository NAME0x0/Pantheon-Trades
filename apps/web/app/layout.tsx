import "../styles/globals.css";
import type { Metadata } from "next";
import Link from "next/link";
import { Analytics } from "@vercel/analytics/next";

export const metadata: Metadata = {
  title: "Pantheon Trades",
  description: "AI council prediction-market trading dashboard",
};

const NAV = [
  { href: "/", label: "Overview" },
  { href: "/demo", label: "Demo" },
  { href: "/dashboard", label: "Dashboard" },
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-background font-sans text-foreground antialiased">
        <header className="border-b border-primary/30 bg-background/95 backdrop-blur">
          <nav className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
            <Link
              href="/"
              className="font-mono text-lg tracking-wide text-primary hover:text-primary/80"
            >
              PANTHEON&nbsp;TRADES
            </Link>
            <ul className="flex gap-6 text-sm">
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
        <footer className="mx-auto max-w-6xl border-t border-primary/20 px-6 py-6 text-xs text-muted-foreground">
          AI council deliberates. Areopagus gates. Parthenon anchors on Arc Testnet.
        </footer>
        <Analytics />
      </body>
    </html>
  );
}
