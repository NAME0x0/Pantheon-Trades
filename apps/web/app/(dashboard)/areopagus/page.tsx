export default function Page() {
  return (
    <div className="space-y-3 py-8">
      <div className="text-xs font-mono uppercase tracking-[0.3em] text-pantheon-gold/70">
        Dashboard · Areopagus
      </div>
      <h1 className="font-mono text-3xl text-pantheon-parchment">Areopagus</h1>
      <p className="text-pantheon-marble">
        This view streams from the live Pantheon backend. Start the FastAPI gateway
        and Redis stack to populate it. For a static walkthrough of the system, visit{" "}
        <a className="text-pantheon-gold hover:underline" href="/demo">/demo</a>.
      </p>
    </div>
  );
}
