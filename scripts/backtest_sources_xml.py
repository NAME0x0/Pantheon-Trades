"""Single-shot Gemini source backtest.

Bundles ALL resolved Manifold markets + the 12 Apollo edge sources
into one XML payload, sends it as a single Gemini prompt, parses
the per-market per-source adjustments back, computes Brier deltas,
and emits an adoption recommendation per source.

Why one shot:

  - Gemini's 1M-token context can hold 200+ markets × 12 source
    definitions easily.
  - One call ~ $0.001-0.01 on `gemini-2.5-flash-lite`; the per-market
    approach would have been 200+ calls and per-source × 12 fanout
    on top of that. Bundling cuts the bill by ~3 orders of magnitude.
  - The model sees every market in the same conversation, which lets
    it apply consistent calibration across the batch — useful for
    relative-Brier comparisons.

Honest constraints:

  - Outcomes are NEVER sent to Gemini. The prompt asks for
    `baseline_p` (Gemini's own estimate) + per-source adjustments.
    All Brier comparisons happen locally against the known outcome.
  - Manifold consensus is the baseline to beat. Adoption criterion:
    `brier_with_source < brier_manifold_baseline` on the held-out
    sample with a non-trivial margin.
  - 4 of 12 sources are *circular* on Manifold-only data (basis_arb,
    consensus_delta, orderbook_imbalance, lead_lag) — we still ask
    Gemini about them so the asymmetric output isn't a confound,
    but we flag the verdict as "untestable on this corpus" in the
    summary.

Usage:
    BOULE_LLM_PROVIDER=gemini GEMINI_API_KEY=... \\
      python scripts/backtest_sources_xml.py --n=200
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from statistics import fmean, pstdev
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
ARTIFACTS = ROOT / "artifacts"
TEMP_XML = ARTIFACTS / "_temp_sources_backtest.xml"

for svc_path in (
    ROOT / "packages" / "pantheon-core" / "src",
    ROOT / "services" / "pythia" / "src",
    ROOT / "services" / "boule" / "src",
):
    if str(svc_path) not in sys.path:
        sys.path.insert(0, str(svc_path))


# ─── Source definitions ──────────────────────────────────────────────


SOURCES: list[dict[str, str]] = [
    {
        "name": "basis_arb",
        "mechanism": "Cross-venue spread between Polymarket and a different venue (Kalshi, sportsbooks). Subtracts fees + slippage. Only meaningful when the same question lists on multiple venues.",
        "applies_to": "Cross-venue events: elections, major sports, Fed decisions.",
    },
    {
        "name": "consensus_delta",
        "mechanism": "Manifold play-money consensus vs Polymarket implied. Wide gap → wider council, smaller size.",
        "applies_to": "Any binary market that lists on both Manifold and a paid venue.",
    },
    {
        "name": "orderbook_imbalance",
        "mechanism": "Polymarket L2 book imbalance — depth on bid vs ask side.",
        "applies_to": "Any Polymarket-listed market with a live order book.",
    },
    {
        "name": "perps_signal",
        "mechanism": "Binance perp funding rate z-score + OI delta. Contrarian: extreme positive funding → bearish on UP direction.",
        "applies_to": "Crypto price-target markets (BTC, ETH, SOL, etc.).",
    },
    {
        "name": "cot_positioning",
        "mechanism": "CFTC speculator-net z-score vs 26-week history. Contrarian: crowded longs → bearish.",
        "applies_to": "Futures-backed underlyings: S&P 500, gold, oil, Treasuries, BTC CME.",
    },
    {
        "name": "geopolitical_risk",
        "mechanism": "GDELT 2.0 news volume + tone for a country or theme. High volume + negative tone → elevated risk.",
        "applies_to": "Geopolitics, world events, conflict markets, election risk.",
    },
    {
        "name": "macro_basis",
        "mechanism": "FRED macro release vs operator threshold. tanh-squashed gap, capped ±0.30.",
        "applies_to": "Fed rate decisions, CPI prints, NFP, GDP, breakeven inflation.",
    },
    {
        "name": "attention",
        "mechanism": "Wikipedia pageview velocity z-score vs baseline. Spiking attention → mild YES bias on 'thing happens' markets.",
        "applies_to": "Any entity with a Wikipedia article (people, events, products, places).",
    },
    {
        "name": "onchain_tvl",
        "mechanism": "DeFiLlama TVL deltas + stablecoin mints + protocol yields.",
        "applies_to": "Crypto markets, DeFi-specific binaries, stablecoin events.",
    },
    {
        "name": "crowd_sentiment",
        "mechanism": "Nitter (X/Twitter) RSS sentiment via in-tree VADER-style scorer.",
        "applies_to": "Markets driven by retail flow / social attention. Volatile, scraping-flaky.",
    },
    {
        "name": "lead_lag",
        "mechanism": "TradingView screener — cross-asset technical lead/lag.",
        "applies_to": "Derivative markets where the underlying has a liquid technical proxy.",
    },
    {
        "name": "macro_release_consensus",
        "mechanism": "Aggregated economist forecasts vs market-implied. Wider gap → information asymmetry.",
        "applies_to": "Macro print binaries (CPI, NFP, GDP, ISM).",
    },
]


# ─── Data fetch ──────────────────────────────────────────────────────


async def fetch_resolved_markets(n: int) -> list[dict[str, Any]]:
    """Pull resolved binary markets from Manifold."""
    import httpx

    from pythia.manifold import ManifoldSource

    out: list[dict[str, Any]] = []
    async with httpx.AsyncClient(timeout=20.0) as http:
        src = ManifoldSource(client=http)
        rows = await src.list_markets(limit=1000)
        for m in rows:
            if not m.get("isResolved"):
                continue
            if m.get("outcomeType") != "BINARY":
                continue
            resolution = m.get("resolution")
            if resolution not in ("YES", "NO"):
                continue
            p = m.get("probability")
            if p is None:
                continue
            out.append({
                "id": m.get("id"),
                "question": (m.get("question") or "").strip(),
                "manifold_p": float(p),
                "outcome_yes": 1 if resolution == "YES" else 0,
            })
            if len(out) >= n:
                break
    return out


# ─── XML payload builder ─────────────────────────────────────────────


def build_xml(markets: list[dict[str, Any]]) -> str:
    """Construct the XML payload. Markets carry NO outcome — Gemini
    must not see the answer it's being graded on.
    """
    root = ET.Element("backtest")
    sources_el = ET.SubElement(root, "sources")
    for s in SOURCES:
        ET.SubElement(sources_el, "source", attrib={
            "name": s["name"],
        }).text = (
            f"Mechanism: {s['mechanism']} | Applies to: {s['applies_to']}"
        )
    markets_el = ET.SubElement(root, "markets")
    for m in markets:
        market_el = ET.SubElement(markets_el, "market", attrib={
            "id": str(m["id"]),
            "manifold_p": f"{m['manifold_p']:.4f}",
        })
        ET.SubElement(market_el, "question").text = m["question"]
    return ET.tostring(root, encoding="unicode")


SYSTEM_PROMPT = """You are a calibrated forecaster grading prediction-market questions.

You will receive ONE XML payload containing:
  - A <sources> block: 12 Apollo edge sources with mechanism + applicability descriptions.
  - A <markets> block: N resolved binary questions, each with a `manifold_p` (the Manifold play-money consensus probability before resolution).

For EACH market, you must output:
  1. `baseline_p`: your own probability of YES, ignoring Manifold's prior. Use base rates + general knowledge cut-off. One number in [0.01, 0.99].
  2. For each of the 12 sources: an `applies` flag (yes/no) AND, when applies=yes, an `adjustment` in [-0.10, +0.10] representing how much that source would shift your baseline probability if you had the live data.

CRITICAL RULES:
  - DO NOT use Manifold's `manifold_p` as your baseline. Compute baseline_p independently — Manifold is the benchmark we are trying to beat.
  - When a source is structurally inapplicable to a question (e.g. `perps_signal` for an election market), output `applies="no"` and `adjustment="0.0"`.
  - Adjustments are signed: positive means the source would push YOUR probability UP (toward YES).
  - DO NOT include any prose outside the XML response. No markdown.
  - Output a single <evaluations> root with one <market> per input market, in the same order.
  - Be conservative on adjustments. A 0.05 adjustment is significant.

Response format (strict XML):

<evaluations>
  <market id="...">
    <baseline_p>0.XX</baseline_p>
    <source name="basis_arb" applies="yes" adjustment="-0.02"/>
    <source name="consensus_delta" applies="no" adjustment="0.0"/>
    ... all 12 sources ...
  </market>
  ...
</evaluations>
"""


# ─── Gemini call (one shot) ──────────────────────────────────────────


async def gemini_one_shot(
    system: str,
    user: str,
    model: str,
    *,
    max_retries: int = 4,
) -> dict[str, Any]:
    """Single Gemini v1beta REST call with retries on 429 / 5xx.

    Each retry waits a parsed `retry in Xs` value (capped at 30s) or
    an exponential backoff starting at 4s.
    """
    import httpx

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY missing")

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={api_key}"
    )
    payload = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": {
            "maxOutputTokens": 32_000,
            "temperature": 0.2,
        },
    }

    attempt = 0
    backoff = 4.0
    record: dict[str, Any] = {}
    while True:
        async with httpx.AsyncClient(timeout=600.0) as http:
            t0 = time.perf_counter()
            try:
                resp = await http.post(url, json=payload)
            except (httpx.ReadTimeout, httpx.ConnectError) as exc:
                latency_ms = int((time.perf_counter() - t0) * 1000)
                if attempt >= max_retries:
                    return {
                        "latency_ms": latency_ms,
                        "http_status": 0,
                        "error": f"transport: {type(exc).__name__}",
                        "text": "",
                        "tokens_in": 0,
                        "tokens_out": 0,
                    }
                attempt += 1
                wait_s = min(30.0, backoff * (2 ** (attempt - 1)))
                print(f"      transport error {type(exc).__name__}, retry in {wait_s:.1f}s")
                await asyncio.sleep(wait_s)
                continue
            latency_ms = int((time.perf_counter() - t0) * 1000)
        record = {"latency_ms": latency_ms, "http_status": resp.status_code}
        if resp.status_code in (429, 500, 502, 503, 504) and attempt < max_retries:
            # Parse Gemini's "Please retry in Xs" if present
            wait_s = backoff * (2 ** attempt)
            m = re.search(r"retry in ([0-9.]+)s", resp.text)
            if m:
                try:
                    wait_s = min(30.0, max(2.0, float(m.group(1))))
                except ValueError:
                    pass
            wait_s = min(30.0, wait_s)
            attempt += 1
            print(f"      HTTP {resp.status_code}, retry {attempt}/{max_retries} in {wait_s:.1f}s")
            await asyncio.sleep(wait_s)
            continue
        if resp.status_code != 200:
            record["error"] = resp.text[:1000]
            record["text"] = ""
            record["tokens_in"] = 0
            record["tokens_out"] = 0
            return record
        body = resp.json()
        candidates = body.get("candidates") or []
        text = ""
        if candidates:
            parts = candidates[0].get("content", {}).get("parts") or []
            text = "".join(p.get("text", "") for p in parts)
        usage = body.get("usageMetadata") or {}
        record.update({
            "text": text,
            "tokens_in": int(usage.get("promptTokenCount", 0)),
            "tokens_out": int(usage.get("candidatesTokenCount", 0)),
            "model_version": body.get("modelVersion") or model,
            "finish_reason": candidates[0].get("finishReason") if candidates else None,
            "retries": attempt,
        })
        return record


# ─── Response parse ──────────────────────────────────────────────────


@dataclass
class MarketEval:
    market_id: str
    baseline_p: float
    source_adjustments: dict[str, float] = field(default_factory=dict)
    source_applies: dict[str, bool] = field(default_factory=dict)


def _strip_codefence(text: str) -> str:
    """Models sometimes wrap XML in ```xml fences despite instructions."""
    text = text.strip()
    m = re.search(r"```(?:xml)?\s*(.*?)```", text, re.DOTALL)
    if m:
        return m.group(1).strip()
    return text


def parse_response(text: str) -> list[MarketEval]:
    """Parse the strict <evaluations> XML payload."""
    cleaned = _strip_codefence(text)
    # Try to locate the root tag even if the model added stray prose.
    start = cleaned.find("<evaluations")
    end = cleaned.rfind("</evaluations>")
    if start >= 0 and end > start:
        cleaned = cleaned[start : end + len("</evaluations>")]
    try:
        root = ET.fromstring(cleaned)
    except ET.ParseError as exc:
        raise RuntimeError(f"failed to parse evaluations XML: {exc}\nfirst 400 chars: {cleaned[:400]}")

    out: list[MarketEval] = []
    for m_el in root.findall("market"):
        mid = m_el.get("id") or ""
        baseline_el = m_el.find("baseline_p")
        try:
            baseline = float((baseline_el.text or "0.5").strip()) if baseline_el is not None else 0.5
        except ValueError:
            baseline = 0.5
        baseline = max(0.01, min(0.99, baseline))
        ev = MarketEval(market_id=mid, baseline_p=baseline)
        for s_el in m_el.findall("source"):
            name = s_el.get("name") or ""
            applies = (s_el.get("applies") or "no").lower() == "yes"
            try:
                adj = float(s_el.get("adjustment") or "0.0")
            except ValueError:
                adj = 0.0
            adj = max(-0.10, min(0.10, adj))
            ev.source_adjustments[name] = adj
            ev.source_applies[name] = applies
        out.append(ev)
    return out


# ─── Brier compute ───────────────────────────────────────────────────


def brier(probs: list[float], outcomes: list[int]) -> float:
    if not probs:
        return 0.0
    return sum((p - o) ** 2 for p, o in zip(probs, outcomes)) / len(probs)


def decompose(probs: list[float], outcomes: list[int], n_bins: int = 10) -> dict:
    """Murphy decomposition: brier = reliability − resolution + uncertainty."""
    if not probs:
        return {"reliability": 0.0, "resolution": 0.0, "uncertainty": 0.0, "n": 0}
    n = len(probs)
    base = sum(outcomes) / n
    uncertainty = base * (1 - base)
    bins: list[tuple[list[float], list[int]]] = [([], []) for _ in range(n_bins)]
    for p, o in zip(probs, outcomes):
        idx = min(n_bins - 1, max(0, int(p * n_bins)))
        bins[idx][0].append(p)
        bins[idx][1].append(o)
    rel = 0.0
    res = 0.0
    for ps, os in bins:
        if not ps:
            continue
        bp = sum(ps) / len(ps)
        bo = sum(os) / len(os)
        w = len(ps) / n
        rel += w * (bp - bo) ** 2
        res += w * (bo - base) ** 2
    return {
        "reliability": round(rel, 5),
        "resolution": round(res, 5),
        "uncertainty": round(uncertainty, 5),
        "implied_brier": round(rel - res + uncertainty, 5),
        "n": n,
    }


# ─── Adoption logic ──────────────────────────────────────────────────


def adoption_verdict(
    source: str,
    brier_with: float,
    brier_baseline: float,
    n_applied: int,
    n_total: int,
) -> tuple[str, str]:
    """Return (verdict, reason).

    Adopt if:
      1. Brier with source < Brier baseline by a meaningful margin (≥0.002 absolute).
      2. Source was deemed applicable on ≥5% of markets.
      3. Untestable if applicability < 5% — too few signals to judge.
    """
    if n_total == 0:
        return ("untestable", "no markets in sample")
    appl_rate = n_applied / n_total
    if appl_rate < 0.05:
        return ("untestable", f"applies to only {appl_rate:.1%} of sample (n={n_applied}/{n_total})")
    delta = brier_with - brier_baseline
    if delta < -0.002:
        return ("ADOPT", f"brier improvement {-delta:.4f} on {appl_rate:.1%} of markets")
    if delta > 0.002:
        return ("REJECT", f"brier worse by {delta:.4f} on {appl_rate:.1%} of markets")
    return ("HOLD", f"no meaningful change ({delta:+.4f}) on {appl_rate:.1%} of markets")


# ─── Main ────────────────────────────────────────────────────────────


async def run(n: int, model: str, *, dry_run: bool = False, batch_size: int = 25) -> dict:
    started = datetime.now(timezone.utc).isoformat()
    t_start = time.perf_counter()

    print(f"  pulling {n} resolved Manifold markets...")
    markets = await fetch_resolved_markets(n)
    if not markets:
        return {"error": "no resolved markets"}
    print(f"  got {len(markets)} markets")

    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    # Empirically Gemini flash-lite drops markets when given 96+ in one
    # shot. Batches of ~25 land near-100% reliably. Each batch reuses
    # the same system prompt; only the user XML changes.
    batches: list[list[dict[str, Any]]] = []
    for i in range(0, len(markets), batch_size):
        batches.append(markets[i : i + batch_size])
    print(f"  splitting into {len(batches)} batch(es) of up to {batch_size}")

    evals: list[MarketEval] = []
    llm_records: list[dict[str, Any]] = []

    try:
        if dry_run:
            print("  --dry-run: skipping Gemini calls")
        else:
            for bi, batch in enumerate(batches):
                xml_user = build_xml(batch)
                TEMP_XML.write_text(xml_user, encoding="utf-8")
                print(f"  [batch {bi + 1}/{len(batches)}] {len(batch)} markets, XML {len(xml_user)} bytes...")
                rec = await gemini_one_shot(SYSTEM_PROMPT, xml_user, model=model)
                llm_records.append(rec)
                if rec.get("http_status") != 200:
                    err = rec.get("error", "unknown")
                    raise RuntimeError(
                        f"Gemini call failed on batch {bi + 1}: "
                        f"HTTP {rec.get('http_status')}: {err[:400]}"
                    )
                print(
                    f"  [batch {bi + 1}] {rec['tokens_in']} in / {rec['tokens_out']} out, "
                    f"{rec['latency_ms']}ms"
                )
                try:
                    batch_evals = parse_response(rec["text"])
                except RuntimeError as exc:
                    print(f"  [batch {bi + 1}] parse failed: {exc}")
                    continue
                print(f"  [batch {bi + 1}] parsed {len(batch_evals)} evaluations")
                evals.extend(batch_evals)
    finally:
        # Delete the temp XML per the user's spec.
        if TEMP_XML.exists():
            TEMP_XML.unlink()
            print("  deleted temp XML")

    # Aggregate LLM record across batches.
    llm_record = {
        "tokens_in": sum(r.get("tokens_in", 0) for r in llm_records),
        "tokens_out": sum(r.get("tokens_out", 0) for r in llm_records),
        "latency_ms": sum(r.get("latency_ms", 0) for r in llm_records),
        "model_version": llm_records[0].get("model_version") if llm_records else "",
        "n_batches": len(llm_records),
        "skipped": dry_run,
    }

    if not evals:
        return {
            "error": "no evaluations parsed",
            "llm_record": llm_record,
            "started_at": started,
            "wall_seconds": round(time.perf_counter() - t_start, 2),
        }

    # Index by market id.
    market_by_id = {str(m["id"]): m for m in markets}
    eval_by_id = {ev.market_id: ev for ev in evals}

    # ── Compute Brier scores ────────────────────────────────────────
    manifold_probs: list[float] = []
    baseline_gemini_probs: list[float] = []
    outcomes: list[int] = []
    for mid, ev in eval_by_id.items():
        m = market_by_id.get(mid)
        if m is None:
            continue
        manifold_probs.append(m["manifold_p"])
        baseline_gemini_probs.append(ev.baseline_p)
        outcomes.append(m["outcome_yes"])

    brier_manifold = brier(manifold_probs, outcomes)
    brier_gemini_baseline = brier(baseline_gemini_probs, outcomes)

    # Per-source: brier with the adjustment applied.
    per_source: dict[str, dict] = {}
    for src in SOURCES:
        name = src["name"]
        probs_with: list[float] = []
        outcomes_for_source: list[int] = []
        n_applied = 0
        for mid, ev in eval_by_id.items():
            m = market_by_id.get(mid)
            if m is None:
                continue
            applies = ev.source_applies.get(name, False)
            adj = ev.source_adjustments.get(name, 0.0)
            if applies and adj != 0.0:
                n_applied += 1
            adjusted = max(0.01, min(0.99, ev.baseline_p + adj))
            probs_with.append(adjusted)
            outcomes_for_source.append(m["outcome_yes"])
        brier_with = brier(probs_with, outcomes_for_source)
        delta_vs_manifold = brier_with - brier_manifold
        delta_vs_gemini = brier_with - brier_gemini_baseline
        verdict, reason = adoption_verdict(
            source=name,
            brier_with=brier_with,
            brier_baseline=brier_gemini_baseline,
            n_applied=n_applied,
            n_total=len(probs_with),
        )
        per_source[name] = {
            "n_applied": n_applied,
            "applicability_rate": round(n_applied / max(1, len(probs_with)), 4),
            "mean_abs_adjustment": round(
                fmean([abs(eval_by_id[mid].source_adjustments.get(name, 0.0))
                       for mid in eval_by_id]),
                5,
            ),
            "stdev_adjustment": round(
                pstdev([eval_by_id[mid].source_adjustments.get(name, 0.0)
                        for mid in eval_by_id]),
                5,
            ),
            "brier_with_source": round(brier_with, 5),
            "brier_delta_vs_manifold": round(delta_vs_manifold, 5),
            "brier_delta_vs_gemini": round(delta_vs_gemini, 5),
            "verdict": verdict,
            "reason": reason,
        }

    adopted = [n for n, d in per_source.items() if d["verdict"] == "ADOPT"]
    rejected = [n for n, d in per_source.items() if d["verdict"] == "REJECT"]
    untestable = [n for n, d in per_source.items() if d["verdict"] == "untestable"]
    hold = [n for n, d in per_source.items() if d["verdict"] == "HOLD"]

    return {
        "schema": "pantheon-sources-brier-v1",
        "model": model,
        "started_at": started,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "wall_seconds": round(time.perf_counter() - t_start, 2),
        "n_markets": len(market_by_id),
        "n_evaluations": len(evals),
        "base_rate_yes": round(sum(outcomes) / max(1, len(outcomes)), 4),
        "brier_manifold_baseline": round(brier_manifold, 5),
        "brier_gemini_baseline": round(brier_gemini_baseline, 5),
        "brier_delta_gemini_vs_manifold": round(brier_gemini_baseline - brier_manifold, 5),
        "manifold_decomposition": decompose(manifold_probs, outcomes),
        "gemini_decomposition": decompose(baseline_gemini_probs, outcomes),
        "per_source": per_source,
        "verdicts": {
            "adopt": adopted,
            "reject": rejected,
            "hold": hold,
            "untestable": untestable,
        },
        "llm": {
            "tokens_in": llm_record.get("tokens_in"),
            "tokens_out": llm_record.get("tokens_out"),
            "latency_ms": llm_record.get("latency_ms"),
            "model_version": llm_record.get("model_version"),
            "estimated_cost_usd": round(
                (llm_record.get("tokens_in", 0) / 1_000_000) * 0.10
                + (llm_record.get("tokens_out", 0) / 1_000_000) * 0.40,
                6,
            ),
        },
    }


def _force_load_env():
    """Read .env and overwrite shell env. Same pattern as live_test_gemini.py."""
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip().strip("'").strip('"')
        if v:
            os.environ[k] = v


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=200, help="number of resolved markets")
    parser.add_argument("--model", default="gemini-flash-lite-latest",
                        help="Gemini model id")
    parser.add_argument("--dry-run", action="store_true",
                        help="skip Gemini call, just build + delete the XML")
    args = parser.parse_args()

    _force_load_env()
    if not args.dry_run and not os.environ.get("GEMINI_API_KEY"):
        print("ERROR: GEMINI_API_KEY missing (set in .env or shell)")
        sys.exit(1)

    print(f"backtest_sources_xml: n={args.n} model={args.model}")
    result = asyncio.run(run(args.n, args.model, dry_run=args.dry_run))
    if "error" in result:
        print(f"FAIL: {result['error']}")
        if "llm_record" in result:
            print(f"  LLM record: {result['llm_record']}")
        sys.exit(1)

    out_path = ARTIFACTS / f"sources_brier_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    out_path.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    print()
    print(f"manifold baseline brier: {result['brier_manifold_baseline']:.4f}")
    print(f"gemini   baseline brier: {result['brier_gemini_baseline']:.4f}")
    print()
    print("Per-source verdicts:")
    for name, d in result["per_source"].items():
        marker = "+" if d["verdict"] == "ADOPT" else "-" if d["verdict"] == "REJECT" else "~"
        print(f"  [{marker}] {name:24s}  dBrier(gem) {d['brier_delta_vs_gemini']:+.4f}  "
              f"appl {d['applicability_rate']:.1%}  ->  {d['verdict']}: {d['reason']}")
    print()
    print(f"Done. Artifact: {out_path}")
    print(f"Adopt: {result['verdicts']['adopt']}")
    print(f"Reject: {result['verdicts']['reject']}")
    print(f"Hold: {result['verdicts']['hold']}")
    print(f"Untestable: {result['verdicts']['untestable']}")
    print(f"Cost: ${result['llm']['estimated_cost_usd']:.6f}")


if __name__ == "__main__":
    main()
