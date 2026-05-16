"""Boule deliberation orchestrator.

Four rounds across all council agents:

    R1 opening   -> parallel
    R2 challenge -> parallel
    R3 synthesis -> Athena only
    R4 vote      -> parallel

If any veto-bearing agent (Zeus, Solon) emits a clear veto signal in R1, we
short-circuit the debate immediately rather than burn another two rounds.

Vote tally rules (see docs/CONSTITUTION.md):
  * Quorum: at least MIN_QUORUM agents must cast a non-abstaining vote.
  * Vetoes: any APPROVE from Zeus or Solon is required; an explicit REJECT
    from either is a hard veto regardless of weighted support.
  * Weighted approval: confidence-weighted APPROVE share over participating
    weight must hit APPROVAL_THRESHOLD.

The council probability is the weighted blend of APPROVE voters' probability
estimates. If no one approves, we fall back to the oracle probability — the
debate produced no actionable consensus.
"""

from __future__ import annotations

import asyncio
import pathlib
import time

import structlog

from pantheon_core.direction import directional_edge, infer_direction
from pantheon_core.schema import (
    AgentVote,
    ExitConditions,
    Signal,
    Thesis,
    ThesisBlock,
    utc_now,
)

from boule.agents.base import CouncilAgent
from boule.agents.bear_researcher import Athena, Cassandra
from boule.agents.bull_researcher import Ares, HadesAgent
from boule.agents.execution_agent import Daedalus, Hephaestus, HumansAgent
from boule.agents.risk_manager import Solon, Themis, Zeus
from boule.calibrator import Calibrator
from boule.llm import LLMClient
from boule.trace import Tracer

log = structlog.get_logger("boule.debate")

MIN_QUORUM = 7
APPROVAL_THRESHOLD = 0.60
EARLY_VETO_TOKENS = ("VIOLATION", "VETO", "CONSTITUTIONAL_VIOLATION", "POLICY_VIOLATION")


def _load_prompt(agent_name: str) -> str:
    p = pathlib.Path(__file__).parent / "prompts" / f"{agent_name}.md"
    if p.exists():
        return p.read_text(encoding="utf-8")
    return (
        f"You are {agent_name}, a Pantheon Trades council agent. "
        "Stay in character, reason rigorously, and reply concisely."
    )


def _build_agents(client: LLMClient, tracer: Tracer) -> list[CouncilAgent]:
    return [
        Ares(client, tracer, _load_prompt("ares")),
        HadesAgent(client, tracer, _load_prompt("hades")),
        Athena(client, tracer, _load_prompt("athena")),
        Cassandra(client, tracer, _load_prompt("cassandra")),
        Solon(client, tracer, _load_prompt("solon")),
        Zeus(client, tracer, _load_prompt("zeus")),
        Themis(client, tracer, _load_prompt("themis")),
        Hephaestus(client, tracer, _load_prompt("hephaestus")),
        Daedalus(client, tracer, _load_prompt("daedalus")),
        HumansAgent(client, tracer, _load_prompt("humans")),
    ]


def _is_early_veto(block: ThesisBlock) -> bool:
    upper = block.content.upper()
    return any(token in upper for token in EARLY_VETO_TOKENS)


async def _safe_gather(
    coros: list,
    *,
    label: str,
) -> list:
    """Run agent calls in parallel; on exception, log and substitute a placeholder block."""
    results = await asyncio.gather(*coros, return_exceptions=True)
    cleaned: list = []
    for idx, r in enumerate(results):
        if isinstance(r, Exception):
            log.warning("debate.agent_call_failed", label=label, idx=idx, error=str(r))
            cleaned.append(None)
        else:
            cleaned.append(r)
    return cleaned


def _filter_blocks(blocks: list) -> list[ThesisBlock]:
    return [b for b in blocks if b is not None]


async def run_debate(
    signal: Signal,
    client: LLMClient,
    tracer: Tracer,
    thesis_id: str,
) -> Thesis:
    start = utc_now()
    t0 = time.monotonic()
    await tracer.emit(
        "deliberation_start",
        f"Market {signal.market_id} | edge {signal.edge:+.2%} | band {signal.band}",
    )

    agents = _build_agents(client, tracer)

    # ---- Round 1: openings -------------------------------------------------
    await tracer.emit("agent_round_start", "Round 1 — openings", round=1)
    r1_raw = await _safe_gather([a.opening(signal) for a in agents], label="round1")
    r1: list[ThesisBlock] = _filter_blocks(r1_raw)
    all_blocks: list[ThesisBlock] = list(r1)

    # ---- Early veto short-circuit -----------------------------------------
    early_veto: tuple[str, str] | None = None
    for ag, block in zip(agents, r1_raw):
        if block is None:
            continue
        if ag.has_veto and _is_early_veto(block):
            early_veto = (ag.name, block.content[:200])
            await tracer.emit(
                "veto",
                f"Early veto from {ag.name}: {block.content[:200]}",
                agent=ag.name,
                round=1,
                vote="REJECT",
            )

    # ---- Round 2: challenges ----------------------------------------------
    if early_veto is None:
        await tracer.emit("agent_round_start", "Round 2 — challenges", round=2)
        r2_raw = await _safe_gather(
            [a.challenge(signal, all_blocks) for a in agents], label="round2"
        )
        r2 = _filter_blocks(r2_raw)
        all_blocks.extend(r2)
    else:
        r2 = []

    # ---- Round 3: Athena synthesis ----------------------------------------
    synth_text = ""
    if early_veto is None:
        athena = next((a for a in agents if isinstance(a, Athena)), None)
        if athena is not None:
            try:
                synth = await athena.synthesize(signal, all_blocks)
                all_blocks.append(synth)
                synth_text = synth.content
                await tracer.emit("synthesis", synth.content, agent="athena", round=3)
            except Exception as e:
                log.warning("debate.synthesis_failed", error=str(e))

    # ---- Round 4: votes ----------------------------------------------------
    agent_votes: list[AgentVote] = []
    zeus_veto = solon_veto = bool(early_veto)
    cassandra_flags: list[str] = []
    humans_flags: list[str] = []
    hephaestus_flags: list[str] = []

    calibrator = Calibrator.from_env()

    if early_veto is None:
        await tracer.emit("agent_round_start", "Round 4 — votes", round=4)
        vote_results = await asyncio.gather(
            *[a.vote(signal, synth_text) for a in agents], return_exceptions=True
        )
        for ag, result in zip(agents, vote_results):
            if isinstance(result, Exception):
                log.warning("debate.vote_failed", agent=ag.name, error=str(result))
                vs, conf, prob, flags = "ABSTAIN", 0.0, signal.oracle_probability, []
            else:
                vs, conf, prob, flags = result
            # Apply per-agent calibration to the raw probability estimate
            # before it enters the tally. ABSTAIN votes are exempt — they
            # are not used in the council probability blend.
            raw_prob = prob
            if vs != "ABSTAIN" and calibrator.has(ag.name):
                prob = calibrator.apply(ag.name, raw_prob)
                if abs(prob - raw_prob) > 1e-6:
                    flags = list(flags) + [f"calibrated:{raw_prob:.3f}->{prob:.3f}"]
            av = AgentVote(
                agent=ag.name,
                vote=vs,  # type: ignore[arg-type]
                confidence=conf,
                probability_estimate=prob,
                flags=flags,
                summary=f"{vs} (conf {conf:.0%}, p {prob:.2f})",
            )
            agent_votes.append(av)
            await tracer.emit(
                "vote",
                f"{ag.name}: {vs} p={prob:.2f} c={conf:.2f}",
                agent=ag.name,
                round=4,
                vote=vs,
                confidence=conf,
                probability_estimate=prob,
                flags=flags,
            )
            if ag.name == "zeus" and vs == "REJECT":
                zeus_veto = True
            if ag.name == "solon" and vs == "REJECT":
                solon_veto = True
            if ag.name == "cassandra":
                cassandra_flags = list(flags)
            if ag.name == "humans":
                humans_flags = list(flags)
            if ag.name == "hephaestus":
                hephaestus_flags = list(flags)
    else:
        # Early-veto bypass: synthesise the verdict directly.
        veto_name, veto_note = early_veto
        for ag in agents:
            forced = "REJECT" if ag.name == veto_name else "ABSTAIN"
            agent_votes.append(
                AgentVote(
                    agent=ag.name,
                    vote=forced,  # type: ignore[arg-type]
                    confidence=1.0 if ag.name == veto_name else 0.0,
                    probability_estimate=signal.oracle_probability,
                    flags=["early_veto"] if ag.name == veto_name else [],
                    summary=f"early veto ({veto_name})" if ag.name == veto_name else "skipped",
                )
            )

    # ---- Tally -------------------------------------------------------------
    vcounts: dict[str, int] = {"APPROVE": 0, "REJECT": 0, "ABSTAIN": 0}
    weight_by_name = {a.name: a.weight for a in agents}
    w_approve_conf = 0.0
    w_participating = 0.0
    for av in agent_votes:
        vcounts[av.vote] += 1
        if av.vote == "ABSTAIN":
            continue
        w = weight_by_name.get(av.agent, 1.0)
        w_participating += w
        if av.vote == "APPROVE":
            w_approve_conf += w * av.confidence
    waf = (w_approve_conf / w_participating) if w_participating > 0 else 0.0
    participating = vcounts["APPROVE"] + vcounts["REJECT"]

    # Council probability = weighted average of APPROVE voters' probability estimates.
    approving = [av for av in agent_votes if av.vote == "APPROVE"]
    if approving:
        wp = sum(av.probability_estimate * weight_by_name.get(av.agent, 1.0) for av in approving)
        tw = sum(weight_by_name.get(av.agent, 1.0) for av in approving)
        cp = wp / tw if tw > 0 else signal.oracle_probability
    else:
        cp = signal.oracle_probability

    # Direction is determined by where the council lands vs the market price.
    direction = infer_direction(signal.market_probability, cp)
    signed_edge = directional_edge(signal.market_probability, cp, direction)

    approved = (
        early_veto is None
        and participating >= MIN_QUORUM
        and not zeus_veto
        and not solon_veto
        and waf >= APPROVAL_THRESHOLD
    )
    status = "pending_areopagus" if approved else "rejected"

    end = utc_now()
    ms = int((time.monotonic() - t0) * 1000)
    await tracer.emit(
        "verdict",
        f"{'APPROVED' if approved else 'REJECTED'} | direction={direction} | edge={signed_edge:+.2%} | weight={waf:.0%}",
        vote="APPROVE" if approved else "REJECT",
        confidence=waf,
        probability_estimate=cp,
        flags=cassandra_flags + humans_flags + hephaestus_flags,
    )
    await tracer.emit("deliberation_end", f"Done in {ms}ms")

    return Thesis(
        thesis_id=thesis_id,
        signal_id=signal.signal_id,
        market_id=signal.market_id,
        question=signal.question,
        direction=direction,
        council_probability=cp,
        raw_market_probability=signal.market_probability,
        edge=signed_edge,
        confidence=waf,
        recommended_size_pct=min(0.05 * waf, 0.05),
        exit_conditions=ExitConditions(
            invalidation="Market probability moves against thesis by >10pp",
            target=min(cp + 0.10, 0.95) if direction == "YES" else max(cp - 0.10, 0.05),
            stop=max(signal.market_probability - 0.05, 0.05)
            if direction == "YES"
            else min(signal.market_probability + 0.05, 0.95),
            max_hold_days=min(int(signal.days_to_resolution or 30), 90),
        ),
        agents=agent_votes,
        vote_summary=vcounts,
        weighted_approval=waf,
        zeus_veto=zeus_veto,
        solon_veto=solon_veto,
        cassandra_flags=cassandra_flags,
        humans_flags=humans_flags,
        hephaestus_flags=hephaestus_flags,
        trace_id=tracer.trace_id,
        debate_blocks=all_blocks,
        deliberation_start=start,
        deliberation_end=end,
        deliberation_duration_ms=ms,
        status=status,  # type: ignore[arg-type]
    )
