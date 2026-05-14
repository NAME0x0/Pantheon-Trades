"use client";

import { useEffect, useState } from "react";

type TraceMessage = {
  stream: string;
  id: string;
  data: Record<string, unknown>;
};

const WS_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/^http/, "ws") ?? "ws://localhost:8000";

export default function TracesPage() {
  const [events, setEvents] = useState<TraceMessage[]>([]);
  const [status, setStatus] = useState<"connecting" | "open" | "closed">("connecting");

  useEffect(() => {
    const ws = new WebSocket(`${WS_URL}/ws?streams=boule:traces,boule:theses,strategos:trades`);
    ws.onopen = () => setStatus("open");
    ws.onclose = () => setStatus("closed");
    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data) as TraceMessage;
        if (msg.stream && msg.data) {
          setEvents((prev) => [msg, ...prev].slice(0, 200));
        }
      } catch {
        // ignore heartbeats / malformed
      }
    };
    return () => ws.close();
  }, []);

  return (
    <section>
      <h1 className="font-mono text-3xl text-pantheon-gold">Live traces</h1>
      <p className="text-pantheon-marble">
        WebSocket stream of council events. Status:{" "}
        <span className="font-mono text-pantheon-gold">{status}</span>
      </p>
      <div className="mt-4 space-y-2 font-mono text-xs">
        {events.length === 0 && (
          <div className="text-pantheon-marble/60">Waiting for events…</div>
        )}
        {events.map((e) => (
          <div
            key={`${e.stream}-${e.id}`}
            className="rounded border border-pantheon-gold/20 bg-pantheon-ink/40 p-2"
          >
            <span className="text-pantheon-gold">{e.stream}</span>{" "}
            <span className="text-pantheon-marble/60">{e.id}</span>
            <pre className="mt-1 whitespace-pre-wrap text-pantheon-parchment">
              {JSON.stringify(e.data, null, 2)}
            </pre>
          </div>
        ))}
      </div>
    </section>
  );
}
