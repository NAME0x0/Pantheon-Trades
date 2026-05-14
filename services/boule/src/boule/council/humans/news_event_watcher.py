"""News-event watcher — flag if a relevant news item is fresh + extreme."""

from __future__ import annotations


def flag_news_event(headlines: list[dict]) -> str | None:
    if not headlines:
        return None
    strong = [h for h in headlines if abs(float(h.get("polarity", 0.0))) >= 0.6]
    if not strong:
        return None
    return f"{len(strong)} strong-polarity headlines in window"
