"""Alternate council namespace — re-exports the real agents from ``boule.agents``.

The deliberation pipeline lives in ``boule.agents.*`` and is referenced
by :mod:`boule.debate`. This package is the public-facing taxonomy used
by tooling and the dashboard (gods/demigods/humans/messengers) and
simply re-binds the same agent classes under those names.
"""

from boule.agents.base import CouncilAgent
from boule.agents.bear_researcher import Athena, Cassandra
from boule.agents.bull_researcher import Ares, HadesAgent
from boule.agents.execution_agent import Daedalus, Hephaestus, HumansAgent
from boule.agents.risk_manager import Solon, Themis, Zeus

__all__ = [
    "CouncilAgent",
    "Ares",
    "Athena",
    "Cassandra",
    "Daedalus",
    "HadesAgent",
    "Hephaestus",
    "HumansAgent",
    "Solon",
    "Themis",
    "Zeus",
]
