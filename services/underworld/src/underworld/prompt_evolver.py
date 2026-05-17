"""Reflection-driven prompt evolution.

The Underworld owns post-mortems: it knows which trades failed and why.
When the same failure pattern repeats often enough, we want to evolve
the responsible agent's system prompt to internalise the lesson rather
than relying on humans to notice the trend.

Pipeline:

  broken_assumptions  ->  derive_lessons  ->  propose_edits  -> moirai gate
                                                                |
                                                                v
                                                          apply_edit
                                                          (append marker block
                                                          to agent prompt .md)

Edits are deterministic, idempotent, and audit-friendly. We never
rewrite existing prompt text — we append a single marker-delimited
``## Lessons Learned`` block. If the block already exists, edits are
merged into it; duplicate suggestions are skipped.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from pantheon_core.schema import utc_now

from underworld.lessons import Lesson, derive_lessons

# Markers that bound the auto-managed block in each agent's prompt file.
START_MARKER = "<!-- LESSONS_LEARNED_START -->"
END_MARKER = "<!-- LESSONS_LEARNED_END -->"

# We refuse to evolve an agent's prompt unless its loss sample size has
# crossed this threshold — otherwise we are reacting to noise.
MIN_SAMPLES_FOR_EVOLUTION = 20


@dataclass(frozen=True)
class PromptEdit:
    agent: str
    addition_text: str
    rationale: str
    derived_from_pattern: str
    at: datetime = field(default_factory=utc_now)


def propose_edits(
    broken_assumptions_by_agent: dict[str, list[str]],
    *,
    min_samples: int = MIN_SAMPLES_FOR_EVOLUTION,
) -> list[PromptEdit]:
    """Map broken assumptions to prompt edits, one edit per (agent, pattern).

    Agents below the sample-size floor are skipped — we are not going
    to rewrite the apollo prompt off three bad trades.
    """
    edits: list[PromptEdit] = []
    for agent, assumptions in broken_assumptions_by_agent.items():
        if len(assumptions) < min_samples:
            continue
        for lesson in derive_lessons(assumptions):
            edits.append(
                PromptEdit(
                    agent=agent,
                    addition_text=_format_addition(lesson),
                    rationale=(
                        f"Pattern '{lesson.pattern}' observed "
                        f"{lesson.occurrences}x in recent trades."
                    ),
                    derived_from_pattern=lesson.pattern,
                )
            )
    return edits


def _format_addition(lesson: Lesson) -> str:
    return (
        f"- **{lesson.pattern}** (seen {lesson.occurrences}x): "
        f"{lesson.suggested_rule}"
    )


def apply_edit(edit: PromptEdit, prompt_dir: Path) -> bool:
    """Append the edit's addition into the agent's prompt file. Idempotent.

    Returns True if the prompt changed, False if the addition was
    already present.
    """
    path = prompt_dir / f"{edit.agent}.md"
    if not path.exists():
        raise FileNotFoundError(f"prompt for agent {edit.agent} not found at {path}")
    text = path.read_text(encoding="utf-8")

    if edit.addition_text in text:
        return False  # already there, idempotent

    block = _extract_block(text)
    if block is None:
        # No managed block yet — append one.
        new_block = (
            f"\n\n## Lessons Learned\n"
            f"{START_MARKER}\n"
            f"{edit.addition_text}\n"
            f"{END_MARKER}\n"
        )
        path.write_text(text.rstrip() + new_block, encoding="utf-8")
        return True

    # Existing block — append into it.
    merged = block.rstrip() + "\n" + edit.addition_text + "\n"
    new_text = _replace_block(text, merged)
    path.write_text(new_text, encoding="utf-8")
    return True


def _extract_block(text: str) -> str | None:
    start = text.find(START_MARKER)
    end = text.find(END_MARKER)
    if start == -1 or end == -1 or end < start:
        return None
    return text[start + len(START_MARKER) : end]


def _replace_block(text: str, new_inner: str) -> str:
    start = text.find(START_MARKER)
    end = text.find(END_MARKER)
    if start == -1 or end == -1:
        return text
    head = text[: start + len(START_MARKER)]
    tail = text[end:]
    return head + "\n" + new_inner.strip() + "\n" + tail
