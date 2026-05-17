/**
 * Translate a Boule trace transcript into Sankey {nodes, links}.
 *
 * Input: an array of TraceEvent rows with at least
 *   { event_type, agent?, round?, content? }
 * — matches the shape emitted by services/boule/src/boule/trace.py.
 *
 * Output: nodes per (round, agent) plus an "outcome" sink, links
 * weighted by the simple token count of each agent message and
 * extra summary links from round-4 votes to the final outcome.
 *
 * Vote-bearing events carry an extra "vote" field with APPROVE /
 * REJECT / ABSTAIN; we use that to colour-bias the outcome links.
 */

import type { SankeyNode, SankeyLink } from "@/components/charts/sankey";

export interface TraceEventLike {
  event_type: string;
  agent?: string;
  round?: number;
  content?: string;
  // Optional structured vote (populated for round-4 vote events).
  vote?: "APPROVE" | "REJECT" | "ABSTAIN";
  weight?: number;
}

const OUTCOMES = ["APPROVE", "REJECT", "ABSTAIN"] as const;

export interface SankeyGraph {
  nodes: SankeyNode[];
  links: SankeyLink[];
}

export function buildTraceSankey(events: TraceEventLike[]): SankeyGraph {
  const agentEvents = events.filter(
    (e) => e.event_type === "agent_output" && typeof e.agent === "string" && typeof e.round === "number",
  );

  if (agentEvents.length === 0) return { nodes: [], links: [] };

  const seenNodes = new Map<string, SankeyNode>();
  const links: SankeyLink[] = [];

  // Node id format: "r<round>::<agent>"
  const nodeId = (round: number, agent: string) => `r${round}::${agent}`;

  for (const e of agentEvents) {
    const id = nodeId(e.round!, e.agent!);
    if (!seenNodes.has(id)) {
      seenNodes.set(id, { id, label: `${e.agent} R${e.round}`, round: e.round! });
    }
  }

  // Link every agent's block in round N to the SAME agent's block in
  // round N+1 if it exists. Width = max(20, token-count of source block).
  const byAgent = new Map<string, TraceEventLike[]>();
  for (const e of agentEvents) {
    const arr = byAgent.get(e.agent!) ?? [];
    arr.push(e);
    byAgent.set(e.agent!, arr);
  }
  for (const arr of byAgent.values()) {
    arr.sort((a, b) => (a.round ?? 0) - (b.round ?? 0));
    for (let i = 0; i < arr.length - 1; i += 1) {
      const cur = arr[i];
      const nxt = arr[i + 1];
      const value = Math.max(20, tokenCount(cur.content));
      links.push({
        source: nodeId(cur.round!, cur.agent!),
        target: nodeId(nxt.round!, nxt.agent!),
        value,
      });
    }
  }

  // Outcome sinks (one per APPROVE / REJECT / ABSTAIN). Insert in the
  // round AFTER the deepest agent round so they sit on the right edge.
  const maxRound = Math.max(...agentEvents.map((e) => e.round ?? 0));
  const outcomeRound = maxRound + 1;
  for (const outcome of OUTCOMES) {
    seenNodes.set(outcome, { id: outcome, label: outcome, round: outcomeRound });
  }

  // Final votes -> outcome sinks. Each agent's final round (round 4
  // by Pantheon convention) is the bridge to outcome. If a vote is
  // tagged, use it; otherwise default to ABSTAIN so the link still
  // shows up (kept thin via min weight).
  const finalEvents = agentEvents.filter((e) => e.round === maxRound);
  for (const e of finalEvents) {
    const target = OUTCOMES.includes(e.vote as never) ? (e.vote as string) : "ABSTAIN";
    const weight = Math.max(8, (e.weight ?? 1) * 20);
    links.push({
      source: nodeId(e.round!, e.agent!),
      target,
      value: weight,
      label: `${e.agent} -> ${target}`,
    });
  }

  return {
    nodes: Array.from(seenNodes.values()),
    links,
  };
}

function tokenCount(text?: string): number {
  if (!text) return 1;
  return Math.max(1, text.split(/\s+/).length);
}
