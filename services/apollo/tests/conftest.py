"""Apollo test fixtures.

Auto-clears the in-process Nitter cache between every test so that
cached results from one test never pollute another. Without this,
the Nitter TTL cache (introduced in Wave 4 of the profitability
build) leaked across the existing Nitter-sentiment suite.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _clear_nitter_cache():
    """Run before each test."""
    try:
        from apollo.sources.nitter import _cache_clear
        _cache_clear()
    except ImportError:
        pass
    yield
