from __future__ import annotations

from moirai.atropos import Atropos
from moirai.clotho import Clotho
from moirai.enforcer import MoiraiEnforcer
from moirai.lachesis import Lachesis
from moirai.laws import StrategyState


def _setup():
    enf = MoiraiEnforcer()
    return enf, Clotho(enf), Lachesis(enf), Atropos(enf)


def test_full_lifecycle_walks_to_live():
    enf, clotho, lachesis, _ = _setup()
    rec = clotho.spin("momentum-v1")
    assert rec.state is StrategyState.DRAFT
    ok, _ = clotho.register(rec.strategy_id)
    assert ok
    ok, _ = lachesis.to_paper(rec.strategy_id)
    assert ok
    # Need metrics to satisfy promotion gates.
    rec.paper_trades = 12
    rec.brier_score = 0.18
    rec.sharpe = 0.8
    rec.win_rate = 0.55
    result = lachesis.promote(rec.strategy_id)
    assert result.promoted


def test_promotion_blocks_with_insufficient_trades():
    enf, clotho, lachesis, _ = _setup()
    rec = clotho.spin("strat")
    clotho.register(rec.strategy_id)
    lachesis.to_paper(rec.strategy_id)
    rec.paper_trades = 3
    rec.brier_score = 0.18
    rec.sharpe = 0.8
    rec.win_rate = 0.55
    result = lachesis.promote(rec.strategy_id)
    assert not result.promoted


def test_atropos_force_terminate_irreversible():
    enf, clotho, _, atropos = _setup()
    rec = clotho.spin("strat")
    atropos.force_terminate(rec.strategy_id, "kill")
    assert rec.state is StrategyState.TERMINATED
    ok, _ = enf.transition(rec.strategy_id, StrategyState.LIVE)
    assert not ok


def test_cooling_applied_blocks_eligibility():
    enf, clotho, lachesis, _ = _setup()
    rec = clotho.spin("strat")
    clotho.register(rec.strategy_id)
    lachesis.to_paper(rec.strategy_id)
    enf.apply_cooling(rec.strategy_id, "failed_thesis")
    eligible, reason = enf.is_eligible_for_deliberation(rec.strategy_id)
    assert not eligible
    assert "cooling" in reason.lower()
