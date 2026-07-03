"""Backward-compatible import path — ``NsxtApi`` now lives in
:mod:`nsxt_robot.keywords.assertions`. Existing ``import nsxt_robot.api`` or
``from nsxt_robot.api import NsxtApi`` continues to work unchanged.
"""

from __future__ import annotations

from .keywords.assertions import NsxtApi

__all__ = ["NsxtApi"]
