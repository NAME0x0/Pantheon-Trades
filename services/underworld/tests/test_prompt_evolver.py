"""Tests for the reflection-driven prompt evolver."""

from __future__ import annotations

from pathlib import Path

import pytest

from underworld.prompt_evolver import (
    END_MARKER,
    MIN_SAMPLES_FOR_EVOLUTION,
    START_MARKER,
    PromptEdit,
    apply_edit,
    propose_edits,
)


def test_propose_edits_skips_under_sample_floor():
    edits = propose_edits({"apollo": ["overconfident_probability_estimate"] * 3})
    assert edits == []


def test_propose_edits_emits_for_each_promoted_pattern():
    assumptions = ["overconfident_probability_estimate"] * MIN_SAMPLES_FOR_EVOLUTION
    edits = propose_edits({"apollo": assumptions})
    assert len(edits) == 1
    edit = edits[0]
    assert edit.agent == "apollo"
    assert "overconfident_probability_estimate" in edit.addition_text
    assert edit.derived_from_pattern == "overconfident_probability_estimate"


def test_propose_edits_uses_lesson_rule_text():
    edits = propose_edits({"apollo": ["stale_data"] * 25})
    assert len(edits) == 1
    assert "stale" in edits[0].addition_text.lower()


def test_propose_edits_multi_pattern_per_agent():
    sizes_threshold = MIN_SAMPLES_FOR_EVOLUTION
    assumptions = (
        ["overconfident_probability_estimate"] * sizes_threshold
        + ["stale_data"] * sizes_threshold
    )
    edits = propose_edits({"athena": assumptions})
    # derive_lessons aggregates by pattern — both should promote.
    patterns = {e.derived_from_pattern for e in edits}
    assert patterns == {"overconfident_probability_estimate", "stale_data"}


def test_apply_edit_appends_new_block(tmp_path: Path):
    prompt = tmp_path / "apollo.md"
    prompt.write_text("# Apollo\n\nbody\n", encoding="utf-8")
    edit = PromptEdit(
        agent="apollo",
        addition_text="- **x**: do the thing",
        rationale="repeat pattern x",
        derived_from_pattern="x",
    )
    changed = apply_edit(edit, tmp_path)
    assert changed is True
    new_text = prompt.read_text(encoding="utf-8")
    assert "## Lessons Learned" in new_text
    assert START_MARKER in new_text
    assert END_MARKER in new_text
    assert "- **x**: do the thing" in new_text


def test_apply_edit_idempotent(tmp_path: Path):
    prompt = tmp_path / "apollo.md"
    prompt.write_text("# Apollo\n\nbody\n", encoding="utf-8")
    edit = PromptEdit(
        agent="apollo",
        addition_text="- **x**: do the thing",
        rationale="",
        derived_from_pattern="x",
    )
    apply_edit(edit, tmp_path)
    again = apply_edit(edit, tmp_path)
    assert again is False
    text = prompt.read_text(encoding="utf-8")
    assert text.count("- **x**: do the thing") == 1


def test_apply_edit_merges_into_existing_block(tmp_path: Path):
    prompt = tmp_path / "apollo.md"
    prompt.write_text(
        f"# Apollo\nbody\n\n## Lessons Learned\n{START_MARKER}\n- old line\n{END_MARKER}\n",
        encoding="utf-8",
    )
    edit = PromptEdit(
        agent="apollo",
        addition_text="- **y**: new lesson",
        rationale="",
        derived_from_pattern="y",
    )
    apply_edit(edit, tmp_path)
    text = prompt.read_text(encoding="utf-8")
    assert "- old line" in text
    assert "- **y**: new lesson" in text
    # And still has the markers.
    assert text.count(START_MARKER) == 1
    assert text.count(END_MARKER) == 1


def test_apply_edit_raises_when_prompt_missing(tmp_path: Path):
    edit = PromptEdit(
        agent="ghost",
        addition_text="- nothing",
        rationale="",
        derived_from_pattern="missing",
    )
    with pytest.raises(FileNotFoundError):
        apply_edit(edit, tmp_path)
