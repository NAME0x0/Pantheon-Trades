"use client";

export default function Error({ error, reset }: { error: Error; reset: () => void }) {
  return (
    <div className="space-y-4 py-16 text-center">
      <h1 className="font-mono text-3xl text-pantheon-gold">Something broke</h1>
      <p className="text-pantheon-marble">{error.message}</p>
      <button
        onClick={reset}
        className="rounded-md border border-pantheon-gold/40 px-4 py-2 font-mono text-sm text-pantheon-marble hover:bg-pantheon-gold/10"
      >
        Try again
      </button>
    </div>
  );
}
