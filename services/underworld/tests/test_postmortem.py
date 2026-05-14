from __future__ import annotations

from underworld.postmortem import PostMortemRunner


def test_loss_with_overconfidence_flags_broken_assumption():
    runner = PostMortemRunner()
    pm = runner.run(
        thesis_id="t1",
        market_id="m1",
        direction="YES",
        entry_probability=0.75,
        resolution_probability=0.20,
        pnl_pct=-0.30,
        agent_predictions={"ares": 0.80, "hades": 0.30},
    )
    assert pm.outcome == "loss"
    assert "overconfident_probability_estimate" in pm.broken_assumptions
    assert pm.agent_accuracy["hades"] is True
    assert pm.agent_accuracy["ares"] is False


def test_win_without_assumption_breaks():
    runner = PostMortemRunner()
    pm = runner.run(
        thesis_id="t2",
        market_id="m2",
        direction="YES",
        entry_probability=0.65,
        resolution_probability=0.95,
        pnl_pct=0.40,
        agent_predictions={"ares": 0.70, "hades": 0.55},
    )
    assert pm.outcome == "win"
    assert pm.broken_assumptions == []


def test_push_outcome():
    runner = PostMortemRunner()
    pm = runner.run(
        thesis_id="t3",
        market_id="m3",
        direction="YES",
        entry_probability=0.55,
        resolution_probability=0.55,
        pnl_pct=0.0005,
        agent_predictions={},
    )
    assert pm.outcome == "push"
