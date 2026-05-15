"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Pause, Play, RotateCcw, SkipForward, Zap } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

type TraceEvent = {
  event_id: string;
  sequence: number;
  event_type:
    | "deliberation_start"
    | "deliberation_end"
    | "agent_round_start"
    | "agent_output"
    | "synthesis"
    | "vote"
    | "veto"
    | "verdict";
  agent: string | null;
  round: number | null;
  content: string;
  tokens: number | null;
  latency_ms: number | null;
  vote: "APPROVE" | "REJECT" | "ABSTAIN" | null;
  confidence: number | null;
  probability_estimate: number | null;
  flags: string[];
  timestamp: string;
};

type Bundle = {
  scenario: string;
  source: string;
  provider: string;
  model: string;
  signal: {
    market_id: string;
    question: string;
    category: string;
    market_probability: number;
    oracle_probability: number;
    edge: number;
    band: string;
    band_score: number;
    liquidity_score: number;
    spread: number;
    staleness_seconds: number;
    volume_24h: number;
    open_interest: number;
    data_sources: string[];
  };
  events: TraceEvent[];
  thesis: {
    direction: "YES" | "NO";
    council_probability: number;
    weighted_approval: number;
    confidence: number;
    recommended_size_pct: number;
    zeus_veto: boolean;
    solon_veto: boolean;
    vote_summary: Record<string, number>;
    agents: Array<{
      agent: string;
      vote: "APPROVE" | "REJECT" | "ABSTAIN";
      confidence: number;
      probability_estimate: number;
      flags: string[];
    }>;
    deliberation_duration_ms: number;
  };
  verdict:
    | { kind: "approval"; decision: string; final_size_pct: number; kelly_fraction: number; note: string }
    | { kind: "rejection"; reason_code: string; note: string };
  paper_trade: null | {
    direction: "YES" | "NO";
    size_usdc: number;
    entry_price: number;
    fill_price: number;
    status: string;
  };
  deliberation_seconds: number;
};

const SPEEDS = [
  { label: "1×", ms: 900 },
  { label: "2×", ms: 450 },
  { label: "4×", ms: 220 },
  { label: "16×", ms: 60 },
];

export function ReplayPlayer({ scenario }: { scenario: string }) {
  const router = useRouter();
  const [bundle, setBundle] = useState<Bundle | null>(null);
  const [loadErr, setLoadErr] = useState<string | null>(null);
  const [cursor, setCursor] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speedIdx, setSpeedIdx] = useState(1);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const url = `/demo/btc-120k-${scenario}.json`;
    setBundle(null);
    setLoadErr(null);
    setCursor(0);
    setPlaying(false);
    fetch(url)
      .then((r) => {
        if (!r.ok) throw new Error(`fetch ${url}: ${r.status}`);
        return r.json();
      })
      .then((j) => setBundle(j as Bundle))
      .catch((e) => setLoadErr(String(e)));
  }, [scenario]);

  const events = bundle?.events ?? [];
  const finished = cursor >= events.length;

  useEffect(() => {
    if (!playing || finished) return;
    const ms = SPEEDS[speedIdx].ms;
    timer.current = setTimeout(() => setCursor((c) => c + 1), ms);
    return () => {
      if (timer.current) clearTimeout(timer.current);
    };
  }, [playing, cursor, finished, speedIdx]);

  useEffect(() => {
    if (finished) setPlaying(false);
  }, [finished]);

  const visible = events.slice(0, cursor);
  const latest = visible[visible.length - 1];

  const reset = useCallback(() => {
    setCursor(0);
    setPlaying(false);
  }, []);
  const skipToEnd = useCallback(() => {
    setCursor(events.length);
    setPlaying(false);
  }, [events.length]);
  const onTabChange = useCallback(
    (v: string) => {
      router.push(`/demo?scenario=${v}`);
    },
    [router],
  );

  return (
    <div className="space-y-6">
      <Tabs value={scenario} onValueChange={onTabChange}>
        <TabsList>
          <TabsTrigger value="approve">Approval</TabsTrigger>
          <TabsTrigger value="restraint">Proof of Restraint</TabsTrigger>
        </TabsList>
      </Tabs>

      {loadErr && (
        <Card className="border-destructive/40 bg-destructive/10">
          <CardContent className="p-6 text-sm text-destructive">
            Could not load demo bundle: {loadErr}
          </CardContent>
        </Card>
      )}

      {!bundle && !loadErr && (
        <Card>
          <CardContent className="p-8 text-center text-muted-foreground">
            Loading deliberation…
          </CardContent>
        </Card>
      )}

      {bundle && (
        <TooltipProvider delayDuration={150}>
          <SignalCard signal={bundle.signal} />

          <Card>
            <CardContent className="flex flex-wrap items-center gap-3 p-4">
              <Button onClick={() => setPlaying((p) => !p)} disabled={finished}>
                {playing ? <Pause /> : <Play />}
                {playing ? "Pause" : "Play"}
              </Button>
              <Button variant="outline" onClick={reset}>
                <RotateCcw />
                Reset
              </Button>
              <Button variant="outline" onClick={skipToEnd}>
                <SkipForward />
                Skip to verdict
              </Button>
              <div className="ml-auto flex items-center gap-2">
                <span className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
                  Speed
                </span>
                {SPEEDS.map((s, i) => (
                  <Button
                    key={s.label}
                    size="sm"
                    variant={i === speedIdx ? "default" : "outline"}
                    onClick={() => setSpeedIdx(i)}
                  >
                    {s.label}
                  </Button>
                ))}
              </div>
              <div className="w-full space-y-1">
                <Progress
                  value={events.length === 0 ? 0 : (visible.length / events.length) * 100}
                />
                <div className="font-mono text-[10px] text-muted-foreground">
                  {visible.length} / {events.length} events
                </div>
              </div>
            </CardContent>
          </Card>

          <div className="grid gap-4 md:grid-cols-3">
            <div className="md:col-span-2">
              <TraceFeed events={visible} latestId={latest?.event_id} />
            </div>
            <div className="space-y-4">
              <VoteBoard thesis={bundle.thesis} visible={visible} />
              {finished && <VerdictCard bundle={bundle} />}
            </div>
          </div>
        </TooltipProvider>
      )}
    </div>
  );
}

function SignalCard({ signal }: { signal: Bundle["signal"] }) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-baseline justify-between gap-3 space-y-0 p-5 pb-3">
        <div>
          <div className="text-xs uppercase tracking-wider text-muted-foreground">Signal</div>
          <CardTitle className="mt-1 text-lg">{signal.question}</CardTitle>
        </div>
        <Badge variant={bandVariant(signal.band)}>Band {signal.band}</Badge>
      </CardHeader>
      <CardContent className="grid grid-cols-2 gap-y-3 px-5 pb-5 text-sm md:grid-cols-4">
        <Field label="Market p" value={pct(signal.market_probability)} />
        <Field label="Oracle p" value={pct(signal.oracle_probability)} />
        <Field
          label="Edge"
          value={`${signal.edge >= 0 ? "+" : ""}${pct(signal.edge)}`}
          tone={signal.edge > 0 ? "good" : "bad"}
        />
        <Field label="Score" value={signal.band_score.toFixed(3)} />
        <Field label="Liquidity" value={signal.liquidity_score.toFixed(3)} />
        <Field label="Spread" value={pct(signal.spread)} />
        <Field label="Volume 24h" value={`$${(signal.volume_24h / 1000).toFixed(0)}k`} />
        <Field label="Staleness" value={`${signal.staleness_seconds}s`} />
      </CardContent>
    </Card>
  );
}

function TraceFeed({
  events,
  latestId,
}: {
  events: TraceEvent[];
  latestId?: string;
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    const last = containerRef.current.querySelector("[data-latest]");
    last?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [latestId]);

  return (
    <Card>
      <CardContent
        ref={containerRef}
        className="h-[600px] space-y-2 overflow-y-auto p-4"
      >
        {events.length === 0 ? (
          <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
            Press <Play className="mx-1 inline size-3" /> Play to begin
          </div>
        ) : (
          events.map((e) => (
            <EventCard key={e.event_id} event={e} latest={e.event_id === latestId} />
          ))
        )}
      </CardContent>
    </Card>
  );
}

function EventCard({ event, latest }: { event: TraceEvent; latest: boolean }) {
  const ring = latest ? "ring-1 ring-primary/60" : "";
  const dataAttr = latest ? { "data-latest": true } : {};

  switch (event.event_type) {
    case "deliberation_start":
    case "deliberation_end":
      return (
        <div
          {...dataAttr}
          className={cn(
            "rounded-md border border-primary/20 bg-card/40 px-3 py-2 font-mono text-xs uppercase tracking-wider text-primary/80",
            ring,
          )}
        >
          {event.content}
        </div>
      );
    case "agent_round_start":
      return (
        <div
          {...dataAttr}
          className={cn(
            "rounded-md bg-primary/10 px-3 py-2 font-mono text-sm text-primary",
            ring,
          )}
        >
          ── {event.content} ──
        </div>
      );
    case "veto":
      return (
        <div
          {...dataAttr}
          className={cn(
            "rounded-md border-2 border-destructive/60 bg-destructive/10 p-3",
            ring,
          )}
        >
          <div className="flex items-center gap-1.5 font-mono text-xs uppercase tracking-wider text-destructive">
            <Zap className="size-3" /> Veto · {event.agent}
          </div>
          <div className="mt-1 text-sm text-destructive-foreground">{event.content}</div>
        </div>
      );
    case "verdict":
      return (
        <div
          {...dataAttr}
          className={cn(
            "rounded-md border border-primary/40 bg-primary/10 p-3",
            ring,
          )}
        >
          <div className="font-mono text-xs uppercase tracking-wider text-primary">
            Council verdict
          </div>
          <div className="mt-1 font-mono text-sm text-foreground">{event.content}</div>
        </div>
      );
    case "vote":
      return (
        <div
          {...dataAttr}
          className={cn(
            "flex items-center justify-between rounded-md border border-primary/20 bg-card/40 px-3 py-2 text-sm",
            ring,
          )}
        >
          <span className="font-mono text-foreground">{event.agent}</span>
          <Badge variant={voteVariant(event.vote)}>
            {event.vote} · p {event.probability_estimate?.toFixed(2)} · c{" "}
            {event.confidence?.toFixed(2)}
          </Badge>
        </div>
      );
    case "synthesis":
      return (
        <div
          {...dataAttr}
          className={cn(
            "rounded-md border border-primary/40 bg-card/70 p-3",
            ring,
          )}
        >
          <div className="font-mono text-xs uppercase tracking-wider text-primary">
            Athena · Synthesis
          </div>
          <div className="mt-2 text-sm leading-relaxed text-foreground">{event.content}</div>
        </div>
      );
    case "agent_output":
    default: {
      const metaLine = [
        event.latency_ms ? `${event.latency_ms}ms` : null,
        event.tokens ? `${event.tokens} tok` : null,
      ]
        .filter(Boolean)
        .join(" · ");
      return (
        <div
          {...dataAttr}
          className={cn(
            "rounded-md border border-primary/15 bg-card/30 p-3",
            ring,
          )}
        >
          <div className="flex items-center justify-between font-mono text-xs">
            <span className="text-primary">
              {event.agent} · R{event.round}
            </span>
            {metaLine && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <span className="cursor-help text-muted-foreground/70">{metaLine}</span>
                </TooltipTrigger>
                <TooltipContent>Provider latency · response tokens</TooltipContent>
              </Tooltip>
            )}
          </div>
          <div className="mt-2 text-sm text-muted-foreground">{event.content}</div>
        </div>
      );
    }
  }
}

function VoteBoard({
  thesis,
  visible,
}: {
  thesis: Bundle["thesis"];
  visible: TraceEvent[];
}) {
  const castVotes = useMemo(() => {
    const m = new Map<string, { vote: string; confidence: number; probability: number }>();
    for (const e of visible) {
      if (e.event_type === "vote" && e.agent && e.vote) {
        m.set(e.agent, {
          vote: e.vote,
          confidence: e.confidence ?? 0,
          probability: e.probability_estimate ?? 0,
        });
      }
    }
    return m;
  }, [visible]);

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm uppercase tracking-wider">Vote board</CardTitle>
      </CardHeader>
      <CardContent>
        <ul className="space-y-1.5">
          {thesis.agents.map((a) => {
            const cast = castVotes.get(a.agent);
            return (
              <li key={a.agent} className="flex items-center justify-between text-sm">
                <span className="font-mono text-foreground">{a.agent}</span>
                {cast ? (
                  <Badge variant={voteVariant(cast.vote)}>{cast.vote}</Badge>
                ) : (
                  <Badge variant="muted">pending</Badge>
                )}
              </li>
            );
          })}
        </ul>
      </CardContent>
    </Card>
  );
}

function VerdictCard({ bundle }: { bundle: Bundle }) {
  const { verdict, paper_trade, thesis } = bundle;

  if (verdict.kind === "rejection") {
    return (
      <Card className="border-destructive/40 bg-destructive/10">
        <CardHeader className="pb-2">
          <div className="font-mono text-xs uppercase tracking-wider text-destructive">
            Areopagus verdict
          </div>
          <CardTitle className="text-2xl text-destructive">REJECTED</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <Badge variant="destructive">Reason · {verdict.reason_code}</Badge>
          <p className="text-sm text-destructive-foreground/80">{verdict.note}</p>
          <Card className="border-primary/30 bg-primary/5">
            <CardContent className="p-3">
              <div className="font-mono text-xs uppercase tracking-wider text-primary">
                Proof of Restraint
              </div>
              <div className="mt-1 text-xs text-muted-foreground">
                Areopagus will write this rejection as a cryptographic witness to the{" "}
                <code className="font-mono">ProofOfRestraint</code> contract on Arc Testnet.
                The council declined to trade. The decision is anchored on-chain.
              </div>
            </CardContent>
          </Card>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-primary/50 bg-primary/5">
      <CardHeader className="pb-2">
        <div className="font-mono text-xs uppercase tracking-wider text-primary">
          Areopagus verdict
        </div>
        <CardTitle className="text-2xl text-foreground">{verdict.decision}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <dl className="space-y-1 text-sm">
          <Row label="Direction" value={thesis.direction} />
          <Row label="Council p" value={pct(thesis.council_probability)} />
          <Row label="Weighted approval" value={pct(thesis.weighted_approval)} />
          <Row label="Half-Kelly" value={verdict.kelly_fraction.toFixed(3)} />
          <Row label="Final size" value={pct(verdict.final_size_pct)} />
        </dl>
        <p className="text-xs text-muted-foreground">{verdict.note}</p>
        {paper_trade && (
          <Card>
            <CardContent className="p-3">
              <div className="font-mono text-xs uppercase tracking-wider text-primary">
                Paper trade · Strategos
              </div>
              <dl className="mt-2 space-y-1 text-sm">
                <Row label="Direction" value={paper_trade.direction} />
                <Row label="Size" value={`$${paper_trade.size_usdc.toFixed(2)} USDC`} />
                <Row label="Fill price" value={paper_trade.fill_price.toFixed(3)} />
                <Row label="Status" value={paper_trade.status} />
              </dl>
            </CardContent>
          </Card>
        )}
      </CardContent>
    </Card>
  );
}

function Field({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone?: "good" | "bad";
}) {
  const color =
    tone === "good"
      ? "text-emerald-300"
      : tone === "bad"
      ? "text-rose-300"
      : "text-foreground";
  return (
    <div>
      <div className="text-xs uppercase tracking-wider text-muted-foreground">{label}</div>
      <div className={cn("font-mono", color)}>{value}</div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="font-mono text-foreground">{value}</dd>
    </div>
  );
}

function bandVariant(band: string): "success" | "default" | "warning" | "muted" {
  switch (band) {
    case "A":
      return "success";
    case "B":
      return "default";
    case "C":
      return "warning";
    default:
      return "muted";
  }
}

function voteVariant(
  vote: string | null | undefined,
): "success" | "destructive" | "muted" {
  switch (vote) {
    case "APPROVE":
      return "success";
    case "REJECT":
      return "destructive";
    default:
      return "muted";
  }
}

function pct(n: number): string {
  return `${(n * 100).toFixed(2)}%`;
}
