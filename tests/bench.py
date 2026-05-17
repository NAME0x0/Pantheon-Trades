"""End-to-end benchmark for the Pantheon Trades stack.

Probes correctness + speed without external services:

  1. Syntax-check every Python source.
  2. Live Arc Testnet RPC: chain id, latest block, USDC system contract.
  3. Per-service pytest sweep (10 service suites + the integration test).
  4. Microbenchmarks:
       * Apollo score_market throughput
       * Apollo prefilter + scoring with FeatureCache
       * Areopagus court.evaluate_thesis throughput
       * PaperBook execute + settle latency
       * Parthenon keccak content_hash + Merkle build for n leaves
       * Boule run_debate latency with FakeAnthropic (zero-network)

Prints one report. Exit code is non-zero only if a correctness check fails;
slow microbench numbers print but do not fail the run.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (
    ROOT / "packages" / "pantheon-core" / "src",
    ROOT / "services" / "apollo" / "src",
    ROOT / "services" / "boule" / "src",
    ROOT / "services" / "areopagus" / "src",
    ROOT / "services" / "strategos" / "src",
    ROOT / "services" / "argos" / "src",
    ROOT / "services" / "parthenon" / "src",
    ROOT / "services" / "ostrakon" / "src",
    ROOT / "services" / "moirai" / "src",
    ROOT / "services" / "underworld" / "src",
    ROOT / "apps" / "api" / "src",
):
    sys.path.insert(0, str(p))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

CHECK = "OK"
FAIL = "FAIL"


@dataclass
class Section:
    title: str
    ok: bool = True
    notes: list[str] = field(default_factory=list)
    metrics: list[tuple[str, str]] = field(default_factory=list)


def _hr(t: str) -> None:
    print(f"\n===== {t} =====")


def _line(label: str, value: str, width: int = 38) -> str:
    return f"  {label.ljust(width)} {value}"


def _percentiles(samples_ms: list[float]) -> tuple[float, float, float]:
    s = sorted(samples_ms)
    n = len(s)
    p50 = s[max(0, n // 2)]
    p95 = s[max(0, int(0.95 * (n - 1)))]
    p99 = s[max(0, int(0.99 * (n - 1)))]
    return p50, p95, p99


def time_block(fn, repeats: int) -> list[float]:
    timings: list[float] = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        fn()
        timings.append((time.perf_counter() - t0) * 1000.0)
    return timings


# ---------------------------------------------------------------------------
# 1. Syntax check
# ---------------------------------------------------------------------------

def bench_syntax() -> Section:
    _hr("syntax check")
    section = Section(title="syntax")
    result = subprocess.run(
        [sys.executable, str(ROOT / "tests" / "_syntax_check.py")],
        capture_output=True,
        text=True,
    )
    section.ok = result.returncode == 0
    out = (result.stdout or "").strip()
    for line in out.splitlines():
        print(line)
    section.notes.append(out.splitlines()[0] if out else "(no output)")
    return section


# ---------------------------------------------------------------------------
# 2. Arc Testnet probe
# ---------------------------------------------------------------------------

def bench_arc() -> Section:
    _hr("arc testnet probe")
    section = Section(title="arc")
    try:
        from pantheon_api.config import settings
        from web3 import Web3
        w3 = Web3(Web3.HTTPProvider(settings.rpc_url, request_kwargs={"timeout": 10}))
        chain_id = w3.eth.chain_id
        block = w3.eth.block_number
        gas = w3.eth.gas_price
        section.metrics.append(("rpc_url", settings.rpc_url))
        section.metrics.append(("chain_id", str(chain_id)))
        section.metrics.append(("latest_block", f"{block:,}"))
        section.metrics.append(("gas_price_gwei", f"{gas / 1e9:.2f}"))
        section.ok = chain_id == settings.arc_chain_id
        if not section.ok:
            section.notes.append(f"chain id mismatch: expected {settings.arc_chain_id}, got {chain_id}")
    except Exception as e:
        section.ok = False
        section.notes.append(f"arc probe failed: {e!r}")
        print(f"  arc probe failed: {e!r}")
        return section
    for label, val in section.metrics:
        print(_line(label, val))
    return section


# ---------------------------------------------------------------------------
# 3. pytest sweep
# ---------------------------------------------------------------------------

PYTEST_TARGETS = [
    ("pantheon-core", ["packages/pantheon-core/src"], "packages/pantheon-core/tests"),
    ("areopagus", ["packages/pantheon-core/src", "services/areopagus/src"], "services/areopagus/tests"),
    ("boule", ["packages/pantheon-core/src", "services/boule/src"], "services/boule/tests"),
    ("apollo", ["packages/pantheon-core/src", "services/apollo/src"], "services/apollo/tests"),
    ("argos", ["packages/pantheon-core/src", "services/argos/src"], "services/argos/tests"),
    ("strategos", ["packages/pantheon-core/src", "services/strategos/src"], "services/strategos/tests"),
    ("parthenon", ["packages/pantheon-core/src", "services/parthenon/src"], "services/parthenon/tests"),
    ("ostrakon", ["packages/pantheon-core/src", "services/ostrakon/src"], "services/ostrakon/tests"),
    ("moirai", ["packages/pantheon-core/src", "services/moirai/src"], "services/moirai/tests"),
    ("underworld", ["packages/pantheon-core/src", "services/underworld/src"], "services/underworld/tests"),
]

INTEGRATION_TARGET = (
    "integration",
    [
        "packages/pantheon-core/src",
        "services/apollo/src",
        "services/boule/src",
        "services/areopagus/src",
        "services/strategos/src",
        "services/argos/src",
    ],
    "tests/test_pipeline_integration.py",
)

SEP = ";" if os.name == "nt" else ":"


def _run_pytest(name: str, py_path_parts: list[str], target: str) -> tuple[bool, int, float, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = SEP.join(str(ROOT / p) for p in py_path_parts)
    t0 = time.perf_counter()
    result = subprocess.run(
        [sys.executable, "-m", "pytest", str(ROOT / target), "-q", "--tb=line"],
        capture_output=True,
        text=True,
        env=env,
        cwd=ROOT,
    )
    elapsed = time.perf_counter() - t0
    out = (result.stdout or "") + (result.stderr or "")
    last = [ln.strip() for ln in out.strip().splitlines() if ln.strip()]
    summary = ""
    passed = 0
    for ln in reversed(last):
        if "passed" in ln or "failed" in ln or "error" in ln:
            summary = ln
            break
    for token in summary.split():
        if token.isdigit():
            passed = int(token)
            break
    return (result.returncode == 0), passed, elapsed, summary


def bench_pytest() -> Section:
    _hr("pytest sweep")
    section = Section(title="pytest")
    all_ok = True
    total_passed = 0
    total_time = 0.0
    for name, py_paths, target in PYTEST_TARGETS:
        ok, passed, elapsed, summary = _run_pytest(name, py_paths, target)
        all_ok = all_ok and ok
        if ok:
            total_passed += passed
        total_time += elapsed
        status = CHECK if ok else FAIL
        print(_line(f"{name:14s} [{status}]", f"{summary} ({elapsed:.2f}s)"))
        if not ok:
            section.notes.append(f"{name}: {summary}")

    ok, passed, elapsed, summary = _run_pytest(*INTEGRATION_TARGET)
    all_ok = all_ok and ok
    total_time += elapsed
    if ok:
        total_passed += passed
    print(_line(f"{'integration':14s} [{CHECK if ok else FAIL}]", f"{summary} ({elapsed:.2f}s)"))
    if not ok:
        section.notes.append(f"integration: {summary}")

    section.ok = all_ok
    section.metrics.append(("total_passed", str(total_passed)))
    section.metrics.append(("total_time_s", f"{total_time:.2f}"))
    return section


# ---------------------------------------------------------------------------
# 4. forge tests
# ---------------------------------------------------------------------------

def bench_forge() -> Section:
    _hr("foundry tests")
    section = Section(title="forge")
    forge = (Path.home() / ".foundry" / "bin" / "forge.exe")
    if not forge.exists():
        forge = (Path.home() / ".foundry" / "bin" / "forge")
    if not forge.exists():
        section.ok = False
        section.notes.append("forge not installed")
        print("  forge not installed — skipping")
        return section
    t0 = time.perf_counter()
    result = subprocess.run(
        [str(forge), "test", "--root", str(ROOT / "contracts"), "-q"],
        capture_output=True,
        text=True,
    )
    elapsed = time.perf_counter() - t0
    section.ok = result.returncode == 0
    out = (result.stdout or "") + (result.stderr or "")
    summary = ""
    for ln in reversed(out.strip().splitlines()):
        if "tests passed" in ln or "failed" in ln:
            summary = ln.strip()
            break
    print(_line("forge test", f"{summary} ({elapsed:.2f}s)"))
    section.metrics.append(("summary", summary))
    section.metrics.append(("elapsed_s", f"{elapsed:.2f}"))
    return section


# ---------------------------------------------------------------------------
# 5. Microbenchmarks
# ---------------------------------------------------------------------------

def _make_snapshot():
    from apollo.features.catalyst import CatalystEvent
    from apollo.features.sentiment import SentimentSample
    from apollo.scorer import MarketSnapshot

    return MarketSnapshot(
        market_id="bench-m",
        question="Will the benchmark pass?",
        category="other",
        market_probability=0.40,
        bid=0.39,
        ask=0.41,
        volume_24h=300_000,
        open_interest=600_000,
        price_history=[0.30, 0.32, 0.36, 0.38, 0.40, 0.41, 0.42, 0.44, 0.45, 0.43],
        price_std_24h=0.04,
        price_mean=0.40,
        catalysts=[CatalystEvent("event", 12, 0.85)],
        sentiment_samples=[SentimentSample(0.6, 2.0)],
        data_sources=["bench"],
        snapshot_at=datetime.now(timezone.utc),
        staleness_seconds=10,
        source_trust_score=0.95,
        days_to_resolution=14.0,
        sentiment_adjustment=0.08,
        trend_adjustment=0.04,
        catalyst_adjustment=0.05,
    )


def bench_apollo_scorer() -> Section:
    _hr("microbench: apollo score_market")
    from apollo.scorer import score_market

    snap = _make_snapshot()
    samples = time_block(lambda: score_market(snap), repeats=2_000)
    p50, p95, p99 = _percentiles(samples)
    section = Section(title="apollo.score_market")
    section.metrics.append(("samples", "2000"))
    section.metrics.append(("p50_ms", f"{p50:.3f}"))
    section.metrics.append(("p95_ms", f"{p95:.3f}"))
    section.metrics.append(("p99_ms", f"{p99:.3f}"))
    section.metrics.append(("throughput_per_sec", f"{1000.0 / max(p50, 1e-6):,.0f}"))
    for k, v in section.metrics:
        print(_line(k, v))
    return section


def bench_apollo_hotpath() -> Section:
    _hr("microbench: apollo hot-path cache")
    from apollo.hotpath import score_with_cache
    from apollo.latency_budget import LatencyBudget
    from apollo.precompute import FeatureCache

    snap = _make_snapshot()
    cache = FeatureCache(ttl_seconds=60)
    budget = LatencyBudget(total_seconds=10.0)
    # Prime
    score_with_cache(snap, cache, budget)
    samples = time_block(lambda: score_with_cache(snap, cache, budget), repeats=10_000)
    p50, p95, p99 = _percentiles(samples)
    section = Section(title="apollo.hot_path")
    section.metrics.append(("samples", "10000"))
    section.metrics.append(("p50_us", f"{p50 * 1000:.2f}"))
    section.metrics.append(("p95_us", f"{p95 * 1000:.2f}"))
    section.metrics.append(("p99_us", f"{p99 * 1000:.2f}"))
    section.metrics.append(("cache_size", str(cache.size())))
    for k, v in section.metrics:
        print(_line(k, v))
    return section


def bench_areopagus() -> Section:
    _hr("microbench: areopagus court")
    from apollo.scorer import score_market
    from areopagus.court import AreopagusCourt
    from areopagus.gates import PortfolioState
    from pantheon_core.schema import ExitConditions, Thesis

    snap = _make_snapshot()
    signal = score_market(snap)
    thesis = Thesis(
        thesis_id="bench-thesis",
        signal_id=signal.signal_id,
        market_id=signal.market_id,
        question=signal.question,
        direction="YES",
        council_probability=0.58,
        raw_market_probability=signal.market_probability,
        edge=0.18,
        confidence=0.78,
        recommended_size_pct=0.04,
        exit_conditions=ExitConditions(
            invalidation="bench",
            target=0.65,
            stop=0.32,
            max_hold_days=30,
        ),
    )
    court = AreopagusCourt(portfolio=PortfolioState())
    samples = time_block(lambda: court.evaluate_thesis(thesis, signal), repeats=5_000)
    p50, p95, p99 = _percentiles(samples)
    section = Section(title="areopagus.evaluate_thesis")
    section.metrics.append(("samples", "5000"))
    section.metrics.append(("p50_us", f"{p50 * 1000:.2f}"))
    section.metrics.append(("p95_us", f"{p95 * 1000:.2f}"))
    section.metrics.append(("p99_us", f"{p99 * 1000:.2f}"))
    section.metrics.append(("throughput_per_sec", f"{1000.0 / max(p50, 1e-6):,.0f}"))
    for k, v in section.metrics:
        print(_line(k, v))
    return section


def bench_paper_book() -> Section:
    _hr("microbench: strategos paper book")
    from pantheon_core.schema import ApprovalToken, ExitConditions, Thesis
    from strategos.paper import PaperBook

    thesis = Thesis(
        thesis_id="bench-th",
        signal_id="sig",
        market_id="bench-m",
        question="?",
        direction="YES",
        council_probability=0.55,
        raw_market_probability=0.40,
        edge=0.15,
        confidence=0.75,
        recommended_size_pct=0.03,
        exit_conditions=ExitConditions(
            invalidation="x", target=0.55, stop=0.30, max_hold_days=30
        ),
    )
    token = ApprovalToken(
        thesis_id="bench-th",
        decision="APPROVED",
        reason_code="OK",
        note="",
        final_size_pct=0.03,
        kelly_fraction=0.10,
    )

    def cycle():
        book = PaperBook(portfolio_usdc=10_000.0)
        trade = book.execute(token, thesis, mid_price=0.40, depth_usdc=50_000)
        book.settle(trade.trade_id, resolution_yes_price=1.0)

    samples = time_block(cycle, repeats=2_000)
    p50, p95, p99 = _percentiles(samples)
    section = Section(title="strategos.paper.execute_settle")
    section.metrics.append(("samples", "2000"))
    section.metrics.append(("p50_us", f"{p50 * 1000:.2f}"))
    section.metrics.append(("p95_us", f"{p95 * 1000:.2f}"))
    section.metrics.append(("p99_us", f"{p99 * 1000:.2f}"))
    for k, v in section.metrics:
        print(_line(k, v))
    return section


def bench_merkle() -> Section:
    _hr("microbench: parthenon merkle (keccak)")
    from parthenon.hash import content_hash, sha256_hex
    from parthenon.merkle import build_merkle_tree, merkle_proof, verify_proof

    leaf_count = 64
    leaves = [sha256_hex({"i": i, "data": "x" * 100}) for i in range(leaf_count)]

    def build_and_verify():
        root, layers = build_merkle_tree(leaves)
        proof = merkle_proof(layers, 0)
        verify_proof(leaves[0], proof, root)

    samples_build = time_block(lambda: build_merkle_tree(leaves), repeats=500)
    samples_full = time_block(build_and_verify, repeats=500)
    samples_hash = time_block(lambda: content_hash({"sample": "payload"}), repeats=10_000)
    p50_b, p95_b, _ = _percentiles(samples_build)
    p50_f, p95_f, _ = _percentiles(samples_full)
    p50_h, _, _ = _percentiles(samples_hash)
    section = Section(title="parthenon.merkle")
    section.metrics.append(("leaves", str(leaf_count)))
    section.metrics.append(("build_p50_us", f"{p50_b * 1000:.1f}"))
    section.metrics.append(("build_p95_us", f"{p95_b * 1000:.1f}"))
    section.metrics.append(("build+verify_p50_us", f"{p50_f * 1000:.1f}"))
    section.metrics.append(("content_hash_p50_us", f"{p50_h * 1000:.2f}"))
    for k, v in section.metrics:
        print(_line(k, v))
    return section


def bench_boule_fakellm() -> Section:
    _hr("microbench: boule run_debate (fake LLM)")
    section = Section(title="boule.run_debate(fake)")

    async def _run():
        from boule.debate import run_debate
        from pantheon_core.schema import (
            Signal,
            TraceEvent,
            utc_now,
        )

        from boule.llm.base import CompletionResult

        vote_text = (
            "VOTE: APPROVE\nCONFIDENCE: 0.78\nPROBABILITY: 0.62\nFLAGS: NONE\nREASON: bench"
        )
        opening_text = "Opening assessment: bench."

        class _Anthropic:
            async def complete(self, *, system, messages, max_tokens):
                user = messages[-1]["content"] if messages else ""
                return CompletionResult(
                    text=vote_text if "VOTE: APPROVE|REJECT|ABSTAIN" in user else opening_text,
                    tokens=280,
                )

            async def close(self):
                return None

        class _Tracer:
            def __init__(self):
                self.trace_id = "bench-trace"
                self.thesis_id = "bench-th"
                self.signal_id = "bench-sig"
                self.market_id = "bench-m"
                self._seq = 0

            async def emit(self, event_type, content, **kwargs):
                self._seq += 1
                return TraceEvent(
                    trace_id=self.trace_id,
                    thesis_id=self.thesis_id,
                    signal_id=self.signal_id,
                    market_id=self.market_id,
                    event_type=event_type,
                    content=content,
                    timestamp=utc_now(),
                    sequence=self._seq,
                    **{k: v for k, v in kwargs.items() if v is not None},
                )

        signal = Signal(
            signal_id="bench-sig",
            market_id="bench-m",
            question="Will the bench pass?",
            category="other",
            market_probability=0.40,
            oracle_probability=0.58,
            edge=0.18,
            edge_abs=0.18,
            band="A",
            band_score=0.78,
            liquidity_score=0.85,
            volatility_score=0.4,
            catalyst_score=0.7,
            sentiment_score=0.65,
            correlation_score=0.7,
            trend_score=0.7,
            volume_24h=200_000,
            open_interest=400_000,
            bid=0.39,
            ask=0.41,
            spread=0.02,
            data_sources=["bench"],
            staleness_seconds=10,
            source_trust_score=0.95,
            pythia_snapshot_at=utc_now(),
            days_to_resolution=14.0,
        )

        durations: list[float] = []
        for _ in range(3):
            tracer = _Tracer()
            client = _Anthropic()
            t0 = time.perf_counter()
            thesis = await run_debate(signal=signal, client=client, tracer=tracer, thesis_id="bench-th")
            durations.append((time.perf_counter() - t0) * 1000.0)
            assert thesis.status == "pending_areopagus", thesis.status
        return durations

    durations = asyncio.run(_run())
    avg = sum(durations) / len(durations)
    section.metrics.append(("runs", str(len(durations))))
    section.metrics.append(("avg_ms", f"{avg:.1f}"))
    section.metrics.append(("min_ms", f"{min(durations):.1f}"))
    section.metrics.append(("max_ms", f"{max(durations):.1f}"))
    for k, v in section.metrics:
        print(_line(k, v))
    return section


def bench_argos() -> Section:
    _hr("microbench: argos exit rules")
    from argos.exits import check_exit
    from argos.pnl import Position

    pos = Position(
        trade_id="t",
        market_id="m",
        direction="YES",
        entry_price=0.40,
        size_usdc=1_000.0,
        entered_at=datetime.now(timezone.utc) - timedelta(hours=1),
        target=0.55,
        stop=0.30,
        current_price=0.46,
    )
    samples = time_block(lambda: check_exit(pos), repeats=20_000)
    p50, p95, p99 = _percentiles(samples)
    section = Section(title="argos.check_exit")
    section.metrics.append(("samples", "20000"))
    section.metrics.append(("p50_us", f"{p50 * 1000:.2f}"))
    section.metrics.append(("p95_us", f"{p95 * 1000:.2f}"))
    section.metrics.append(("p99_us", f"{p99 * 1000:.2f}"))
    for k, v in section.metrics:
        print(_line(k, v))
    return section


# ---------------------------------------------------------------------------
# 6. Final report
# ---------------------------------------------------------------------------

def main() -> int:
    print("Pantheon Trades — full-stack bench")
    print(f"started_at = {datetime.now(timezone.utc).isoformat()}")

    sections: list[Section] = []
    sections.append(bench_syntax())
    sections.append(bench_arc())
    sections.append(bench_pytest())
    sections.append(bench_forge())
    sections.append(bench_apollo_scorer())
    sections.append(bench_apollo_hotpath())
    sections.append(bench_areopagus())
    sections.append(bench_paper_book())
    sections.append(bench_merkle())
    sections.append(bench_argos())
    sections.append(bench_boule_fakellm())

    _hr("summary")
    failed: list[str] = []
    for s in sections:
        status = CHECK if s.ok else FAIL
        print(f"  [{status}] {s.title}")
        for note in s.notes:
            print(f"          note: {note}")
        if not s.ok and s.title in {"syntax", "arc", "pytest", "forge"}:
            failed.append(s.title)

    if failed:
        print(f"\nbench FAILED: {failed}")
        return 1
    print("\nbench OK — every correctness gate green")
    return 0


if __name__ == "__main__":
    sys.exit(main())
