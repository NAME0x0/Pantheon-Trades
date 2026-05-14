"use client";

import { useEffect, useState } from "react";

const WS_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/^http/, "ws") ?? "ws://localhost:8000";

export type StreamEvent = {
  stream: string;
  id: string;
  data: any;
};

export function useStream(streams: string[]): { events: StreamEvent[]; status: string } {
  const [events, setEvents] = useState<StreamEvent[]>([]);
  const [status, setStatus] = useState<string>("connecting");

  useEffect(() => {
    if (typeof window === "undefined") return;
    const url = `${WS_URL}/ws?streams=${streams.join(",")}`;
    const ws = new WebSocket(url);
    ws.onopen = () => setStatus("open");
    ws.onclose = () => setStatus("closed");
    ws.onerror = () => setStatus("error");
    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data) as StreamEvent;
        if (msg.stream && msg.data) {
          setEvents((prev) => [msg, ...prev].slice(0, 200));
        }
      } catch {
        // ignore heartbeats
      }
    };
    return () => ws.close();
  }, [streams.join(",")]);

  return { events, status };
}
