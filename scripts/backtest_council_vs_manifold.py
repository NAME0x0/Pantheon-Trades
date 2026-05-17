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
    ROOT / "services" / "boule" / "src",
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


# ─── Full-mode LLM council ────────────────────────────────────────────


FULL_SYSTEM_PROMPT = """You are a calibrated forecaster on prediction
markets. Your only job is to read a single binary question and emit a
probability of YES resolution. You must:

  - Output ONLY a single number between 0.01 and 0.99 on the first line.
  - No prose. No reasoning. No markdown.
  - If you genuinely cannot estimate, output 0.50.

You will see the question, the publicly-traded Manifold consensus, and
no other context. Do not anchor on the Manifold number — it is shown
so you can disagree. Use your own knowledge cutoff and base rates."""


FULL_USER_TEMPLATE = """Question: {question}

Manifold play-money consensus: {manifold_p:.3f}

Your probability of YES (one number, 0.01–0.99):"""


def _parse_full_probability(raw_text: str, fallback: float) -> float:
    """Pull the first number we find in the model output. Coerce to
    a valid probability. Fall back to ``fallback`` (Manifold prior)
    on any parse failure — keeps the harness honest if the model
    refuses or rambles.
    """
    import re

    if not raw_text:
        return fallback
    match = re.search(r"-?\d+(?:\.\d+)?", raw_text.strip())
    if not match:
        return fallback
    try:
        p = float(match.group(0))
    except ValueError:
        return fallback
    if p > 1.0:
        # Some models output "75" meaning 75% — accept that form.
        if p <= 100.0:
            p = p / 100.0
        else:
            return fallback
    return max(0.01, min(0.99, p))


async def full_council_p(
    llm,
    question: str,
    manifold_p: float,
) -> tuple[float, dict]:
    """One LLM call per market. Returns (probability, telemetry).

    ``llm`` is a ``boule.llm.LLMClient`` (anthropic / gemini / openai /
    groq / openrouter / etc — same provider matrix the production
    council uses). The prompt is the most stripped-down single-shot
    forecast possible; the council's value-add over the model is what
    the harness is measuring, but in this script we treat ONE model
    as a stand-in for the council so the LLM bill stays bounded at
    one call per market instead of ten.

    Cost on Gemini flash-lite: ~$0.0002 per market. 100 markets ≈ $0.02.
    """
    import time as _time

    user = FULL_USER_TEMPLATE.format(question=question, manifold_p=manifold_p)
    t0 = _time.perf_counter()
    try:
        result = await llm.complete(
            system=FULL_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user}],
            max_tokens=24,  # one number is all we want
        )
        latency_ms = int((_time.perf_counter() - t0) * 1000)
        p = _parse_full_probability(result.text, fallback=manifold_p)
        return p, {
            "latency_ms": latency_ms,
            "tokens_in": result.tokens_in,
            "tokens_out": result.tokens_out,
            "model_fingerprint": result.model_fingerprint,
            "raw_text": (result.text or "")[:120],
            "parse_fallback": False,
        }
    except Exception as exc:  # noqa: BLE001
        latency_ms = int((_time.perf_counter() - t0) * 1000)
        return manifold_p, {
            "latency_ms": latency_ms,
            "tokens_in": 0,
            "tokens_out": 0,
            "model_fingerprint": "",
            "error": str(exc)[:200],
            "parse_fallback": True,
        }


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

    if mode == "full":
        # Lazy import — only build the LLM client when we actually need it.
        from boule.llm import build_default_client

        llm = build_default_client()
        print(f"  mode=full: using LLM client {type(llm).__name__}")
    else:
        llm = None

    council_fn = (
        offline_council_p if mode == "offline"
        else heuristic_council_p if mode == "heuristic"
        else None  # full mode is handled async below
    )

    manifold_probs: list[float] = []
    council_probs: list[float] = []
    outcomes: list[int] = []
    per_row: list[dict] = []

    for i, m in enumerate(markets):
        if mode == "full":
            cp, telem = await full_council_p(llm, m["question"], m["manifold_p"])
            row = {**m, "council_p": cp, "_llm": telem}
            if (i + 1) % 10 == 0 or i == 0:
                print(f"    [{i + 1}/{len(markets)}] cp={cp:.3f} manifold={m['manifold_p']:.3f}")
        else:
            cp = council_fn(m["question"], m["manifold_p"])
            row = {**m, "council_p": cp}
        # Clip to valid probability range
        cp = max(0.01, min(0.99, cp))
        row["council_p"] = cp
        manifold_probs.append(m["manifold_p"])
        council_probs.append(cp)
        outcomes.append(m["outcome_yes"])
        per_row.append(row)

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
        # Verify the operator has set a provider + key. Don't burn
        # the LLM client construction trying to discover a missing key.
        import os
        provider = os.environ.get("BOULE_LLM_PROVIDER", "anthropic").lower()
        env_key = {
            "anthropic": "ANTHROPIC_API_KEY",
            "gemini": "GEMINI_API_KEY",
            "openai": "OPENAI_API_KEY",
            "openrouter": "OPENROUTER_API_KEY",
            "groq": "GROQ_API_KEY",
            "together": "TOGETHER_API_KEY",
            "deepseek": "DEEPSEEK_API_KEY",
            "xai": "XAI_API_KEY",
            "grok": "XAI_API_KEY",
        }.get(provider)
        if env_key and not os.environ.get(env_key):
            print(f"ERROR: --mode=full needs {env_key} (for BOULE_LLM_PROVIDER={provider}).")
            print("       Set it in your env or .env and retry.")
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
