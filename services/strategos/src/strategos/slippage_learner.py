"""Online learner that refines the static slippage estimate from real fills.

The static ``estimate_slippage`` is a linear-in-size-over-depth heuristic.
Real markets have biases:
  * One market may consistently be quoted thinner than its visible depth.
  * Another may consistently fill *inside* the quoted spread (price improvement).
  * The same market may behave differently at different depth regimes.

This learner accumulates per-(market, depth-bucket) EWMA residuals:

    bias = EWMA( actual_slippage - predicted_slippage )

and refines the next estimate by adding the bias term:

    learned = clip( predicted + bias, 0, MAX_SLIPPAGE )

Depth bucketing keeps the model from over-generalising across regimes —
a thin book and a deep book in the same market are different distributions.
``decay`` controls how fast we forget old fills: 0.05 = effective N≈20.

State is serialisable to / from JSON so we can persist between restarts.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path

from strategos.slippage import MAX_SLIPPAGE, estimate_slippage

DEFAULT_DECAY = 0.05
MIN_DEPTH_BUCKET = 0  # log10(depth=1) bucket
MAX_DEPTH_BUCKET = 8  # 10^8 USDC = effectively unbounded


def _depth_bucket(depth_usdc: float) -> int:
    """Return log10 bucket: ``depth in [10^k, 10^(k+1))`` -> k."""
    if depth_usdc <= 1:
        return MIN_DEPTH_BUCKET
    b = int(math.floor(math.log10(depth_usdc)))
    return max(MIN_DEPTH_BUCKET, min(MAX_DEPTH_BUCKET, b))


def _key(market_id: str, depth_usdc: float) -> str:
    return f"{market_id}|d{_depth_bucket(depth_usdc)}"


@dataclass
class SlippageLearner:
    decay: float = DEFAULT_DECAY
    bias: dict[str, float] = field(default_factory=dict)
    samples: dict[str, int] = field(default_factory=dict)

    def estimate(
        self,
        size_usdc: float,
        depth_usdc: float,
        market_id: str | None = None,
    ) -> float:
        """Return the learned slippage estimate. Falls back to the
        unbiased static estimate when no market_id or no prior data."""
        base = estimate_slippage(size_usdc, depth_usdc)
        if market_id is None or size_usdc <= 0:
            return base
        b = self.bias.get(_key(market_id, depth_usdc), 0.0)
        return max(0.0, min(MAX_SLIPPAGE, base + b))

    def observe(
        self,
        market_id: str,
        actual_slippage: float,
        size_usdc: float,
        depth_usdc: float,
    ) -> None:
        """Fold one fill's residual into the EWMA for its bucket."""
        if size_usdc <= 0:
            return
        predicted = estimate_slippage(size_usdc, depth_usdc)
        residual = float(actual_slippage) - predicted
        k = _key(market_id, depth_usdc)
        prev = self.bias.get(k, 0.0)
        # Standard EWMA: new = (1-α) * prev + α * sample
        self.bias[k] = (1.0 - self.decay) * prev + self.decay * residual
        self.samples[k] = self.samples.get(k, 0) + 1

    # ── persistence ──
    def to_json(self) -> str:
        return json.dumps({"decay": self.decay, "bias": self.bias, "samples": self.samples})

    @classmethod
    def from_json(cls, raw: str) -> "SlippageLearner":
        data = json.loads(raw)
        return cls(
            decay=float(data.get("decay", DEFAULT_DECAY)),
            bias=dict(data.get("bias", {})),
            samples={k: int(v) for k, v in data.get("samples", {}).items()},
        )

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json(), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "SlippageLearner":
        if not path.exists():
            return cls()
        try:
            return cls.from_json(path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            return cls()
