"""The Odds API — consensus sportsbook + politics odds.

`https://the-odds-api.com/` exposes a free-tier REST API that
aggregates pre-game odds across 70+ US + UK + EU sportsbooks. The
500 requests/month free tier is enough to refresh ~16/day with
generous over-cache, which suits our use case: we don't need every
tick, just the consensus implied probability at decision time.

Why this matters for Pantheon: many Polymarket markets re-list events
that already trade on conventional sportsbooks (NFL outcomes,
election outcomes when shifted to "will X win" form, World Cup,
boxing finals). The spread between Polymarket's implied probability
and the sportsbook consensus implied probability is a *clean basis*
that drives the basis-arb signal in Apollo.

Implied probability conversion:

  - American odds  (+150, -110)  → 100 / (odds + 100) for positive,
                                   -odds / (-odds + 100) for negative
  - Decimal odds   (2.50)        → 1 / odds
  - Vig-free probability         → divide each outcome's raw implied
                                   by the sum across outcomes

API docs: https://the-odds-api.com/liveapi/guides/v4/
"""

from __future__ import annotations

import os
from typing import Any, Literal

from pantheon_core.schema import utc_now

from pythia.base import DataSource, SourceSnapshot

API_BASE = "https://api.the-odds-api.com/v4"

Region = Literal["us", "us2", "uk", "eu", "au"]
Market = Literal["h2h", "spreads", "totals", "outrights"]


def american_to_prob(odds: int | float) -> float:
    """Convert American odds (+150 / -110) → implied probability."""
    odds = float(odds)
    if odds > 0:
        return 100.0 / (odds + 100.0)
    return -odds / (-odds + 100.0)


def decimal_to_prob(odds: float) -> float:
    """Convert decimal odds → implied probability."""
    if odds <= 1.0:
        return 0.0
    return 1.0 / float(odds)


def vig_free(raw_probabilities: list[float]) -> list[float]:
    """Strip the bookmaker's overround from a set of implied probabilities.

    For a two-outcome market with raw P(A)=0.55 and P(B)=0.50 (sum=1.05),
    vig-free P(A) = 0.55/1.05 ≈ 0.524.
    """
    total = sum(raw_probabilities)
    if total <= 0:
        return [0.5 for _ in raw_probabilities]
    return [p / total for p in raw_probabilities]


class OddsApiSource(DataSource):
    """Read-only Odds API client.

    The free tier returns `bookmakers` arrays where each entry has a
    `last_update`, a `markets` list, and an `outcomes` list inside
    each market. We aggregate across bookmakers to produce a single
    consensus implied probability per outcome.
    """

    name = "odds_api"
    max_staleness_seconds = 300

    DEFAULT_SPORT = "americanfootball_nfl"
    DEFAULT_REGIONS: tuple[Region, ...] = ("us", "us2")

    def __init__(self, client, api_key: str | None = None) -> None:
        super().__init__(client)
        self._api_key = api_key or os.environ.get("ODDS_API_KEY", "")

    async def fetch(self) -> SourceSnapshot:
        """Smoke fetch: latest NFL h2h odds."""
        events = await self.events(sport=self.DEFAULT_SPORT, markets=("h2h",))
        return SourceSnapshot(
            source=self.name,
            fetched_at=utc_now(),
            data={"events": events},
        )

    async def events(
        self,
        *,
        sport: str,
        markets: tuple[Market, ...] = ("h2h",),
        regions: tuple[Region, ...] = DEFAULT_REGIONS,
        odds_format: Literal["american", "decimal"] = "decimal",
    ) -> list[dict[str, Any]]:
        """List upcoming events for ``sport`` with the requested markets."""
        params = {
            "apiKey": self._api_key,
            "regions": ",".join(regions),
            "markets": ",".join(markets),
            "oddsFormat": odds_format,
        }
        resp = await self._client.get(
            f"{API_BASE}/sports/{sport}/odds",
            params=params,
            timeout=15.0,
        )
        resp.raise_for_status()
        return list(resp.json())

    async def consensus_probability(
        self,
        *,
        sport: str,
        event_id: str | None = None,
        team_name: str | None = None,
    ) -> dict[str, Any] | None:
        """Return the vig-free consensus implied probability for one event.

        Either ``event_id`` or ``team_name`` must be supplied. ``team_name``
        is a fuzzy substring match against the bookmaker outcome names —
        sufficient for our use case where the operator already knows
        which Polymarket market they're checking.

        Returns ``{"team": str, "p_yes": float, "n_books": int, "raw_avg": float}``
        or ``None`` if no matching event / outcome is found.
        """
        events = await self.events(sport=sport, markets=("h2h",))
        for ev in events:
            if event_id and ev.get("id") != event_id:
                continue
            target_team = team_name
            books = ev.get("bookmakers") or []
            if not books:
                continue
            # Collect raw implied probabilities across bookmakers.
            yes_probs: list[float] = []
            no_probs: list[float] = []
            chosen_team: str | None = None
            for b in books:
                for m in (b.get("markets") or []):
                    if m.get("key") != "h2h":
                        continue
                    outcomes = m.get("outcomes") or []
                    if len(outcomes) < 2:
                        continue
                    # Decide which outcome is "yes".
                    if target_team:
                        yes_outcome = next(
                            (o for o in outcomes if target_team.lower() in (o.get("name") or "").lower()),
                            None,
                        )
                        no_outcome = next(
                            (o for o in outcomes if o is not yes_outcome),
                            None,
                        )
                    else:
                        yes_outcome, no_outcome = outcomes[0], outcomes[1]
                    if not yes_outcome or not no_outcome:
                        continue
                    chosen_team = chosen_team or yes_outcome.get("name")
                    try:
                        yp = decimal_to_prob(float(yes_outcome["price"]))
                        np = decimal_to_prob(float(no_outcome["price"]))
                    except (KeyError, TypeError, ValueError):
                        continue
                    vf_yes, vf_no = vig_free([yp, np])
                    yes_probs.append(vf_yes)
                    no_probs.append(vf_no)
            if not yes_probs:
                continue
            avg_yes = sum(yes_probs) / len(yes_probs)
            return {
                "team": chosen_team,
                "p_yes": avg_yes,
                "n_books": len(yes_probs),
                "raw_avg": avg_yes,
            }
        return None
