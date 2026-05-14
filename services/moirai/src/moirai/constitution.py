"""Constitution checks — Moirai's veto over lifecycle transitions.

The Moirai constitution is the off-chain mirror of
``contracts/PantheonConstitution.sol``. Any lifecycle action that would
violate a constitutional clause is rejected here before it can be applied
to the enforcer.
"""

from __future__ import annotations

from dataclasses import dataclass

from moirai.enforcer import StrategyRecord
from moirai.laws import StrategyState


@dataclass
class ConstitutionVerdict:
    permitted: bool
    clause: str
    note: str


def can_promote_to_live(rec: StrategyRecord) -> ConstitutionVerdict:
    """Article 4: only strategies with non-trivial paper history may go live."""
    if rec.state is not StrategyState.PAPER:
        return ConstitutionVerdict(False, "ARTICLE_4", "promotion only permitted from PAPER")
    if rec.paper_trades < 5:
        return ConstitutionVerdict(False, "ARTICLE_4", f"only {rec.paper_trades} paper trades < 5 floor")
    return ConstitutionVerdict(True, "ARTICLE_4", "permitted")


def can_revive(rec: StrategyRecord) -> ConstitutionVerdict:
    """Article 7: TERMINATED is final — strategies cannot be revived."""
    if rec.state is StrategyState.TERMINATED:
        return ConstitutionVerdict(False, "ARTICLE_7", "TERMINATED is irreversible")
    return ConstitutionVerdict(True, "ARTICLE_7", "permitted")
