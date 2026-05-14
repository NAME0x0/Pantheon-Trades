"""Schema repair — coerce raw JSON into a valid Pydantic model.

Boule occasionally receives malformed signal payloads (truncated trace,
missing fields). Try a tolerant coercion first; if it still fails the
caller drops the message.
"""

from __future__ import annotations

import json
from typing import TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


def repair_and_validate(model: type[T], raw: str) -> T | None:
    try:
        return model.model_validate_json(raw)
    except Exception:
        pass
    try:
        data = json.loads(raw)
    except (ValueError, json.JSONDecodeError):
        return None
    try:
        return model.model_validate(data)
    except Exception:
        return None
