import { listRestraint, type RestraintSummary } from "../../lib/api";
import { RestraintCard } from "../../components/restraint-card";

export const dynamic = "force-dynamic";

export default async function RestraintPage() {
  let items: RestraintSummary[];
  try {
    items = (await listRestraint()).items;
  } catch {
    items = [];
  }

  const reasonCounts = items.reduce<Record<string, number>>((acc, e) => {
    acc[e.reason_code] = (acc[e.reason_code] ?? 0) + 1;
    return acc;
  }, {});

  return (
    <section className="space-y-6">
      <header>
        <div className="font-mono text-xs uppercase tracking-[0.3em] text-pantheon-gold/80">
          flagship feature
        </div>
        <h1 className="mt-1 font-mono text-4xl tracking-tight text-pantheon-gold">
          Proof of Restraint
        </h1>
        <p className="mt-2 max-w-3xl text-pantheon-marble">
          Every time the Areopagus refuses to trade, the decision is written
          on-chain. The world sees not just the trades we made, but every
          trade we declined to make — the discipline tax we paid to skip
          marginal alpha.
        </p>
      </header>

      <div className="rounded-lg border border-pantheon-gold/30 bg-pantheon-ink/60 p-5">
        <div className="grid grid-cols-2 gap-6 md:grid-cols-4">
          <Stat label="Total declines" value={items.length} />
          <Stat label="Distinct reasons" value={Object.keys(reasonCounts).length} />
          <Stat
            label="Top reason"
            value={Object.entries(reasonCounts).sort((a, b) => b[1] - a[1])[0]?.[0] ?? "—"}
            mono
          />
          <Stat label="Last 24h" value={items.filter((e) => Date.now() - new Date(e.created_at).getTime() < 86_400_000).length} />
        </div>
      </div>

      {items.length === 0 ? (
        <div className="rounded border border-pantheon-gold/20 px-4 py-6 text-pantheon-marble/70">
          No restraint proofs yet — start the Areopagus consumer with{" "}
          <code className="font-mono">python -m areopagus.cli serve</code>.
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {items.map((entry) => (
            <RestraintCard key={entry.proof_id} entry={entry} />
          ))}
        </div>
      )}
    </section>
  );
}

function Stat({
  label,
  value,
  mono = false,
}: {
  label: string;
  value: number | string;
  mono?: boolean;
}) {
  return (
    <div>
      <div className="text-xs uppercase tracking-wider text-pantheon-marble/70">
        {label}
      </div>
      <div
        className={
          "mt-1 text-2xl " +
          (mono ? "font-mono text-pantheon-gold" : "text-pantheon-parchment")
        }
      >
        {value}
      </div>
    </div>
  );
}
