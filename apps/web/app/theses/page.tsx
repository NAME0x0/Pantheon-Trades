import { listTheses } from "../../lib/api";

export const dynamic = "force-dynamic";

interface ThesisRow {
  thesis_id: string;
  direction: string;
  council_probability: number;
  weighted_approval: number;
  recommended_size_pct: number;
  status: string;
  archived_cid?: string | null;
}

export default async function ThesesPage() {
  let theses: ThesisRow[];
  try {
    theses = (await listTheses()).items as ThesisRow[];
  } catch {
    theses = [];
  }
  return (
    <section>
      <h1 className="font-mono text-3xl text-pantheon-gold">Theses</h1>
      <p className="text-pantheon-marble">
        Council verdicts. Status reflects Areopagus gating + archive state.
      </p>
      <div className="mt-6 grid gap-3">
        {theses.length === 0 && (
          <p className="rounded border border-pantheon-gold/20 px-4 py-6 text-pantheon-marble/70">
            No theses yet — start Boule with{" "}
            <code className="font-mono">python -m boule.cli serve</code>.
          </p>
        )}
        {theses.map((t) => (
          <div
            key={t.thesis_id}
            className="rounded-lg border border-pantheon-gold/30 bg-pantheon-ink/60 p-4"
          >
            <div className="flex items-center justify-between gap-4">
              <div>
                <div className="font-mono text-pantheon-gold">{t.direction}</div>
                <div className="text-xs text-pantheon-marble/70">{t.thesis_id}</div>
              </div>
              <div className="text-right text-sm">
                <div>
                  council p:{" "}
                  <span className="font-mono text-pantheon-parchment">
                    {(t.council_probability * 100).toFixed(1)}%
                  </span>
                </div>
                <div>
                  weighted approval:{" "}
                  <span className="font-mono">
                    {(t.weighted_approval * 100).toFixed(0)}%
                  </span>
                </div>
                <div>
                  recommended size:{" "}
                  <span className="font-mono">
                    {(t.recommended_size_pct * 100).toFixed(2)}%
                  </span>
                </div>
              </div>
            </div>
            <div className="mt-2 flex items-center justify-between text-xs text-pantheon-marble/80">
              <span>status: {t.status}</span>
              {t.archived_cid && (
                <span className="font-mono">cid: {t.archived_cid.slice(0, 18)}…</span>
              )}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
