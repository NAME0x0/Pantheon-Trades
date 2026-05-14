"""Adapter glue that turns raw Pythia payloads into Apollo MarketSnapshots."""

from apollo.sources.polymarket import (
    PolymarketSnapshotBuilder,
    snapshot_from_market_payload,
)

__all__ = ["PolymarketSnapshotBuilder", "snapshot_from_market_payload"]
