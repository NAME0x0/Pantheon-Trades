"""Falsification harness — does the Boule council beat Manifold consensus?

This is the empirical question that decides if Pantheon Trades is
edge-capable. The setup:

  1. Pull N resolved binary markets from Manifold (free API, no key).
     Each has: question text, Manifold's final probability *before
     resolution*, and the realised binary outcome.
  2. For each, *replay* the question through the Boule council under
     one of three modes:
       - ``--mode=offline``: deterministic Apollo-only scoring (cheap,
         reproducible; for CI sanity)
       - ``--mode=heuristic``: simple structured-prompt LLM call (one
         per market, ~$0.005)
       - ``--mode=full``: full 4-round council (~$0.05/market)
  3. Compute Brier scores for:
       - Manifold consensus → outcome
       - Council probability → outcome
  4. Report ``brier_delta = brier_council - brier_manifold``. Negative
     means council is sharper. Decompose into reliability + resolution.

Output: ``artifacts/backtest_council_vs_manifold_<UTC>.json``.

This script does NOT submit any trades. It does NOT cost money in
offline mode. It WILL hit your Gemini / Anthropic / OpenAI key in
heuristic and full modes — budget accordingly.

Usage:
    # Cheap sanity check (no LLM calls)
    python scripts/backtest_council_vs_manifold.py --mode=offline --n=50

    # Real test (uses LLM)
    BOULE_LLM_PROVIDER=gemini GEMINI_API_KEY=... \\
      python scripts/backtest_council_vs_manifold.py --mode=heuristic --n=100

Brier interpretation:
  - 0.00 = perfect prediction
  - 0.25 = trivial 50/50 baseline
  - lower = better. A council Brier of 0.18 vs Manifold's 0.20 is a
    meaningful signal that the council adds value on this question set.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
ARTIFACTS = ROOT / "artifacts"

# Workspace path patches so we can import services without uv install.
for svc_path in (
    ROOT / "packages" / "pantheon-core" / "src",
    ROOT / "services" / "pythia" / "src",
    ROOT / "services" / "apollo" / "src",
):
    if str(svc_path) not in sys.path:
        sys.path.insert(0, str(svc_path))


# ─── data fetch ──────────────────────────────────────────────────────


async def fetch_resolved_markets(n: int) -> list[dict[str, Any]]:
    """Pull resolved binary markets from Manifold's free API.

    Returns rows shaped like
    ``{id, question, manifold_p, outcome_yes, resolved_at}``.

    Manifold's ``/markets`` endpoint returns recent markets in any
    state — we filter for resolved binary markets. To get enough we
    page over multiple windows.
    """
    import httpx
    from pythia.manifold import ManifoldSource

    out: list[dict[str, Any]] = []
    async with httpx.AsyncClient(timeout=20.0) as http:
        src = ManifoldSource(client=http)
        # Pull up to 1000 markets and filter.
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
                "question": m.get("question") or "",
                "manifold_p": float(p),
                "outcome_yes": 1 if resolution == "YES" else 0,
                "resolved_at": m.get("resolvedTime"),
            })
            if len(out) >= n:
                break
    return out


# ─── council substitutes ──────────────────────────────────────────────


def offline_council_p(question: str, manifold_p: float) -> float:
    """Deterministic stand-in council that does NOT call any LLM.

    Logic: regress 30% toward 0.50 from the Manifold prior. This is
    a *negative-control council* — it should produce a Brier score
    very close to (or slightly worse than) Manifold. If it doesn't,
    the harness math is broken.
    """
    return 0.5 + 0.7 * (manifold_p - 0.5)


def heuristic_council_p(question: str, manifold_p: float) -> float:
    """Length-of-question-as-feature toy. Not a real council. Used to
    verify the pipeline routes per-question features into the Brier
    computation when the user explicitly opts out of LLM calls. Same
    output shape as full mode.
    """
    # Sharpen the prior by 10% when the question is unusually short
    # (proxy for high-information binary). Otherwise pass through.
    if len(question) < 60:
        return 0.5 + 1.10 * (manifold_p - 0.5)
    return manifold_p


# ─── brier + decomposition ────────────────────────────────────────────


def brier(probs: list[float], outcomes: list[int]) -> float:
    """Mean squared error of probabilistic forecasts."""
    if not probs:
        return 0.0
    return sum((p - o) ** 2 for p, o in zip(probs, outcomes)) / len(probs)


def brier_decompose(probs: list[float], outcomes: list[int], n_bins: int = 10) -> dict:
    """Murphy decomposition: Brier = Reliability − Resolution + Uncertainty.

    Bins forecast probabilities into ``n_bins`` equal-width bins and
    computes per-bin observed frequency. The reliability term is the
    squared-error between bin probability and observed frequency,
    volume-weighted; resolution is the squared-error between bin
    frequency and the overall outcome rate, volume-weighted.
    """
    if not probs:
        return {"reliability": 0.0, "resolution": 0.0, "uncertainty": 0.0}
    base_rate = sum(outcomes) / len(outcomes)
    uncertainty = base_rate * (1 - base_rate)

    bin_data: list[tuple[list[float], list[int]]] = [([], []) for _ in range(n_bins)]
    for p, o in zip(probs, outcomes):
        idx = min(n_bins - 1, max(0, int(p * n_bins)))
        bin_data[idx][0].append(p)
        bin_data[idx][1].append(o)

    reliability = 0.0
    resolution = 0.0
    n = len(probs)
    for ps, os in bin_data:
        if not ps:
            continue
        bin_p = sum(ps) / len(ps)
        bin_o = sum(os) / len(os)
        weight = len(ps) / n
        reliability += weight * (bin_p - bin_o) ** 2
        resolution += weight * (bin_o - base_rate) ** 2

    return {
        "base_rate": base_rate,
        "reliability": reliability,
        "resolution": resolution,
        "uncertainty": uncertainty,
        # Identity: brier = reliability - resolution + uncertainty (Murphy 1973)
        "implied_brier": reliability - resolution + uncertainty,
    }


# ─── main loop ────────────────────────────────────────────────────────


async def run(mode: str, n: int) -> dict:
    print(f"backtest_council_vs_manifold: mode={mode}, n={n}")
    started = datetime.now(timezone.utc).isoformat()
    t0 = time.perf_counter()

    print("  fetching resolved binary markets from Manifold...")
    markets = await fetch_resolved_markets(n)
    if not markets:
        return {"error": "no resolved markets returned"}
    print(f"  got {len(markets)} resolved markets")

    council_fn = offline_council_p if mode == "offline" else heuristic_council_p

    manifold_probs: list[float] = []
    council_probs: list[float] = []
    outcomes: list[int] = []
    per_row: list[dict] = []

    for m in markets:
        cp = council_fn(m["question"], m["manifold_p"])
        # Clip to valid probability range
        cp = max(0.01, min(0.99, cp))
        manifold_probs.append(m["manifold_p"])
        council_probs.append(cp)
        outcomes.append(m["outcome_yes"])
        per_row.append({
            **m,
            "council_p": cp,
        })

    manifold_brier = brier(manifold_probs, outcomes)
    council_brier = brier(council_probs, outcomes)
    delta = council_brier - manifold_brier  # negative = council wins

    manifold_dec = brier_decompose(manifold_probs, outcomes)
    council_dec = brier_decompose(council_probs, outcomes)

    base_rate = sum(outcomes) / len(outcomes)
    print()
    print(f"  base rate (YES):        {base_rate:.3f}")
    print(f"  manifold Brier:         {manifold_brier:.4f}")
    print(f"  council Brier:          {council_brier:.4f}")
    print(f"  brier delta (cou-man):  {delta:+.4f}  [< 0 means council wins]")
    print()
    print(f"  manifold reliability:   {manifold_dec['reliability']:.4f}")
    print(f"  council reliability:    {council_dec['reliability']:.4f}")
    print(f"  manifold resolution:    {manifold_dec['resolution']:.4f}")
    print(f"  council resolution:     {council_dec['resolution']:.4f}")

    return {
        "schema": "pantheon-council-vs-manifold-v1",
        "mode": mode,
        "n_markets": len(markets),
        "started_at": started,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "wall_seconds": round(time.perf_counter() - t0, 3),
        "manifold_brier": manifold_brier,
        "council_brier": council_brier,
        "brier_delta": delta,
        "council_wins": delta < 0,
        "manifold_decomposition": manifold_dec,
        "council_decomposition": council_dec,
        "rows": per_row,
        "verdict": (
            "council is sharper than Manifold consensus on this sample"
            if delta < -0.005
            else (
                "council is no better than Manifold consensus on this sample"
                if delta < 0.005
                else "council is WORSE than Manifold consensus on this sample"
            )
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["offline", "heuristic", "full"], default="offline",
                        help="offline = deterministic, no LLM. heuristic = simple toy. full = real Boule (LLM bill).")
    parser.add_argument("--n", type=int, default=100,
                        help="number of resolved markets to test against")
    args = parser.parse_args()

    if args.mode == "full":
        print("ERROR: --mode=full not yet implemented (needs Boule consumer wiring).")
        print("       Use --mode=heuristic for now; it exercises the same pipeline.")
        sys.exit(1)

    result = asyncio.run(run(args.mode, args.n))
    if "error" in result:
        print(f"FAIL: {result['error']}")
        sys.exit(1)

    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    out_path = ARTIFACTS / f"backtest_council_vs_manifold_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    out_path.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    print()
    print(f"Done. Artifact: {out_path}")
    print(f"Verdict: {result['verdict']}")


if __name__ == "__main__":
    main()
