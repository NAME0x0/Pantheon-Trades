import "../styles/globals.css";
import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Pantheon Trades",
  description: "AI council prediction-market trading dashboard",
};

const NAV = [
  { href: "/", label: "Overview" },
  { href: "/signals", label: "Signals" },
  { href: "/theses", label: "Theses" },
  { href: "/trades", label: "Trades" },
  { href: "/traces", label: "Traces" },
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="bg-pantheon-ink text-pantheon-parchment">
      <body className="min-h-screen font-sans antialiased">
        <header className="border-b border-pantheon-gold/30 bg-pantheon-ink/95 backdrop-blur">
          <nav className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
            <Link href="/" className="font-mono text-lg tracking-wide text-pantheon-gold">
              PANTHEON&nbsp;TRADES
            </Link>
            <ul className="flex gap-6 text-sm">
              {NAV.map((item) => (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    className="text-pantheon-marble hover:text-pantheon-gold"
                  >
                    {item.label}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>
        </header>
        <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>
        <footer className="mx-auto max-w-6xl border-t border-pantheon-gold/20 px-6 py-6 text-xs text-pantheon-marble/70">
          AI council deliberates. Areopagus gates. Parthenon anchors on Arc Testnet.
        </footer>
      </body>
    </html>
  );
}
