"""Adversarial mode toggle — flips Boule into worst-case bear stress test."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AdversarialConfig:
    enabled: bool = False
    bear_weight_multiplier: float = 2.0
    require_super_majority: bool = True


_GLOBAL = AdversarialConfig()


def current() -> AdversarialConfig:
    return _GLOBAL


def enable() -> AdversarialConfig:
    _GLOBAL.enabled = True
    return _GLOBAL


def disable() -> AdversarialConfig:
    _GLOBAL.enabled = False
    return _GLOBAL
