import Link from "next/link";

export default function NotFound() {
  return (
    <div className="space-y-4 py-16 text-center">
      <h1 className="font-mono text-5xl text-pantheon-gold">404</h1>
      <p className="text-pantheon-marble">The oracle has not seen this route.</p>
      <Link
        href="/"
        className="inline-block rounded-md border border-pantheon-gold/40 px-4 py-2 font-mono text-sm text-pantheon-marble hover:bg-pantheon-gold/10"
      >
        Return to the agora
      </Link>
    </div>
  );
}
