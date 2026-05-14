"""Olympus goal subsystems — each module owns one goal class with its own
metric, evaluation cadence, and dashboard surface.
"""

from olympus.goals.daily_bread import DailyBreadGoal, evaluate_daily_bread
from olympus.goals.forbidden_markets import (
    ForbiddenMarketsRegistry,
    is_forbidden,
)
from olympus.goals.odyssey import OdysseyGoal, evaluate_odyssey
from olympus.goals.oracle_watch import OracleWatchGoal, oracle_health
from olympus.goals.war_room import WarRoomGoal, war_room_alerts

__all__ = [
    "DailyBreadGoal",
    "evaluate_daily_bread",
    "ForbiddenMarketsRegistry",
    "is_forbidden",
    "OdysseyGoal",
    "evaluate_odyssey",
    "OracleWatchGoal",
    "oracle_health",
    "WarRoomGoal",
    "war_room_alerts",
]
