"""News analyst — summarise the news polarity backing a signal."""

from __future__ import annotations


def news_summary(headlines: list[dict]) -> str:
    if not headlines:
        return "no news in window"
    pos = sum(1 for h in headlines if float(h.get("polarity", 0.0)) > 0.1)
    neg = sum(1 for h in headlines if float(h.get("polarity", 0.0)) < -0.1)
    return f"{len(headlines)} headlines, {pos} bullish / {neg} bearish"
